import os
import re
import threading
import time
import zipfile
from html import unescape
from tkinter import BOTH, END, LEFT, RIGHT, VERTICAL, Y, filedialog, messagebox, ttk
import tkinter as tk

try:
    import pythoncom
    import win32com.client as win32_client
except Exception:
    pythoncom = None
    win32_client = None

try:
    from ebooklib import epub
    import ebooklib
except Exception:
    epub = None
    ebooklib = None

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None


APP_TITLE = "EPUB 小说朗读器"


def html_to_text(content: str) -> str:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(" ", strip=True)
        return text.strip()

    cleaned = re.sub(r"<script[\s\S]*?</script>", "", content, flags=re.IGNORECASE)
    cleaned = re.sub(r"<style[\s\S]*?</style>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", "\n", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def split_to_chunks(text: str, chunk_size: int = 100) -> list[str]:
    text = text.replace("\r", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []

    parts = re.split(r"([。！？!?；;\n])", text)
    sentences = []
    for i in range(0, len(parts), 2):
        core = parts[i].strip()
        if not core:
            continue
        ender = parts[i + 1] if i + 1 < len(parts) else ""
        sentence = f"{core}{ender}".strip()
        if sentence:
            sentences.append(sentence)

    chunks = []
    for sent in sentences:
        if len(sent) <= chunk_size:
            chunks.append(sent)
            continue

        start = 0
        while start < len(sent):
            chunks.append(sent[start : start + chunk_size])
            start += chunk_size

    return chunks


def parse_epub_file(epub_path: str) -> list[tuple[str, str]]:
    chapters: list[tuple[str, str]] = []

    if epub is not None and ebooklib is not None:
        try:
            book = epub.read_epub(epub_path)
            doc_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
            for index, item in enumerate(doc_items, start=1):
                try:
                    content = item.get_content().decode("utf-8", errors="ignore")
                except Exception:
                    content = str(item.get_content())

                title = f"第{index}章"
                if BeautifulSoup is not None:
                    soup = BeautifulSoup(content, "html.parser")
                    heading = soup.find(["h1", "h2", "h3"])
                    if heading and heading.get_text(strip=True):
                        title = heading.get_text(strip=True)
                text = html_to_text(content)
                if text:
                    chapters.append((title, text))

            if chapters:
                return chapters
        except Exception:
            chapters = []

    with zipfile.ZipFile(epub_path, "r") as zf:
        html_files = [
            name
            for name in zf.namelist()
            if name.lower().endswith((".xhtml", ".html", ".htm"))
        ]
        html_files.sort()

        for idx, name in enumerate(html_files, start=1):
            content = zf.read(name).decode("utf-8", errors="ignore")
            text = html_to_text(content)
            if text:
                base = os.path.splitext(os.path.basename(name))[0]
                chapters.append((f"{idx}. {base}", text))

    return chapters


class ReaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1100x700")

        self.voices: list[tuple[str, str]] = []

        self.chapters: list[tuple[str, str]] = []
        self.current_chunks: list[str] = []
        self.current_chunk_index = 0

        self.reader_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.voice_id_var = tk.StringVar(value="")
        self.active_voice = None

        self.build_ui()
        self.load_voices()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Button(top, text="导入 EPUB", command=self.import_epub).pack(side=LEFT)

        self.file_var = tk.StringVar(value="未选择文件")
        ttk.Label(top, textvariable=self.file_var).pack(side=LEFT, padx=10)

        main = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        main.pack(fill=BOTH, expand=True)

        left_panel = ttk.Frame(main)
        left_panel.pack(side=LEFT, fill="y")

        ttk.Label(left_panel, text="章节").pack(anchor="w")

        self.chapter_list = tk.Listbox(left_panel, width=34, height=28)
        self.chapter_list.pack(side=LEFT, fill="y")
        self.chapter_list.bind("<<ListboxSelect>>", self.on_chapter_selected)

        scroll = ttk.Scrollbar(left_panel, orient=VERTICAL, command=self.chapter_list.yview)
        scroll.pack(side=RIGHT, fill=Y)
        self.chapter_list.config(yscrollcommand=scroll.set)

        right_panel = ttk.Frame(main)
        right_panel.pack(side=LEFT, fill=BOTH, expand=True, padx=(15, 0))

        ttk.Label(right_panel, text="正文预览").pack(anchor="w")

        self.text_box = tk.Text(right_panel, wrap="word")
        self.text_box.pack(fill=BOTH, expand=True)

        control = ttk.LabelFrame(self.root, text="朗读设置", padding=10)
        control.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(control, text="语音:").grid(row=0, column=0, sticky="w")
        self.voice_combo = ttk.Combobox(control, state="readonly", width=50)
        self.voice_combo.grid(row=0, column=1, sticky="w", padx=6)

        ttk.Label(control, text="语速:").grid(row=0, column=2, sticky="e", padx=(20, 0))
        self.rate_var = tk.IntVar(value=180)
        self.rate_scale = ttk.Scale(control, from_=100, to=300, variable=self.rate_var)
        self.rate_scale.grid(row=0, column=3, sticky="ew", padx=6)

        ttk.Label(control, text="音量:").grid(row=0, column=4, sticky="e", padx=(20, 0))
        self.volume_var = tk.DoubleVar(value=1.0)
        self.volume_scale = ttk.Scale(control, from_=0.1, to=1.0, variable=self.volume_var)
        self.volume_scale.grid(row=0, column=5, sticky="ew", padx=6)

        control.columnconfigure(3, weight=1)
        control.columnconfigure(5, weight=1)

        btns = ttk.Frame(control)
        btns.grid(row=1, column=0, columnspan=6, pady=(10, 0), sticky="w")

        ttk.Button(btns, text="开始朗读", command=self.start_read).pack(side=LEFT)
        ttk.Button(btns, text="暂停", command=self.pause_read).pack(side=LEFT, padx=6)
        ttk.Button(btns, text="继续", command=self.resume_read).pack(side=LEFT, padx=6)
        ttk.Button(btns, text="停止", command=self.stop_read).pack(side=LEFT, padx=6)

        self.status_var = tk.StringVar(value="状态: 就绪")
        ttk.Label(self.root, textvariable=self.status_var, padding=(10, 0, 10, 10)).pack(anchor="w")

    def load_voices(self):
        if pythoncom is None or win32_client is None:
            self.status_var.set("状态: 缺少 pywin32 组件，语音不可用")
            self.voice_combo["values"] = ["Default"]
            self.voice_combo.current(0)
            self.voice_id_var.set("")
            return

        com_initialized = False
        options: list[str] = []
        ids: list[str] = []
        try:
            pythoncom.CoInitialize()
            com_initialized = True
            sapi_voice = win32_client.Dispatch("SAPI.SpVoice")
            tokens = sapi_voice.GetVoices()
            for i in range(tokens.Count):
                token = tokens.Item(i)
                name = str(token.GetDescription())
                token_id = str(token.Id)
                options.append(f"{name} | {token_id}")
                ids.append(token_id)
            self.voices = list(zip(options, ids))
        except Exception as e:
            self.voices = []
            self.status_var.set(f"状态: 语音列表加载失败 ({e})")
        finally:
            if com_initialized:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

        if not options:
            options = ["Default"]
            ids = [""]

        self.voice_combo["values"] = options
        self.voice_combo.current(0)
        self.voice_id_var.set(ids[0])

        def on_voice_change(_event=None):
            idx = self.voice_combo.current()
            if 0 <= idx < len(ids):
                self.voice_id_var.set(ids[idx])

        self.voice_combo.bind("<<ComboboxSelected>>", on_voice_change)

    def import_epub(self):
        path = filedialog.askopenfilename(
            title="选择 EPUB 文件", filetypes=[("EPUB files", "*.epub")]
        )
        if not path:
            return

        self.stop_read()
        self.status_var.set("状态: 正在解析 EPUB...")
        self.root.update_idletasks()

        try:
            chapters = parse_epub_file(path)
        except Exception as e:
            messagebox.showerror("解析失败", f"无法读取该 EPUB 文件:\n{e}")
            self.status_var.set("状态: 解析失败")
            return

        if not chapters:
            messagebox.showwarning("无内容", "未在 EPUB 中提取到可朗读文本。")
            self.status_var.set("状态: 未提取到文本")
            return

        self.chapters = chapters
        self.file_var.set(path)
        self.chapter_list.delete(0, END)
        for title, _ in self.chapters:
            self.chapter_list.insert(END, title)

        self.chapter_list.selection_clear(0, END)
        self.chapter_list.selection_set(0)
        self.chapter_list.activate(0)
        self.on_chapter_selected()

        self.status_var.set(f"状态: 已加载 {len(self.chapters)} 个章节")

    def get_selected_index(self) -> int | None:
        selection = self.chapter_list.curselection()
        if not selection:
            return None
        return selection[0]

    def on_chapter_selected(self, _event=None):
        idx = self.get_selected_index()
        if idx is None:
            return

        _, text = self.chapters[idx]
        self.text_box.delete("1.0", END)
        self.text_box.insert("1.0", text[:120000])

    def start_read(self):
        idx = self.get_selected_index()
        if idx is None or not self.chapters:
            messagebox.showinfo("提示", "请先导入 EPUB 并选择章节。")
            return

        if self.reader_thread and self.reader_thread.is_alive():
            self.stop_read()

        _, text = self.chapters[idx]
        chunks = split_to_chunks(text)
        if not chunks:
            messagebox.showwarning("提示", "当前章节没有可朗读内容。")
            return

        self.current_chunks = chunks
        self.current_chunk_index = 0
        self.stop_event.clear()
        self.pause_event.clear()

        self.reader_thread = threading.Thread(target=self.read_loop, daemon=True)
        self.reader_thread.start()
        self.status_var.set(f"状态: 正在朗读（共 {len(self.current_chunks)} 段）")

    def read_loop(self):
        if pythoncom is None or win32_client is None:
            self.root.after(0, lambda: messagebox.showerror("语音引擎错误", "未安装 pywin32，无法朗读。"))
            self.root.after(0, lambda: self.status_var.set("状态: 缺少 pywin32"))
            return

        com_initialized = False
        try:
            pythoncom.CoInitialize()
            com_initialized = True
            voice = win32_client.Dispatch("SAPI.SpVoice")
        except Exception as e:
            self.root.after(0, lambda err=e: messagebox.showerror("语音引擎错误", f"初始化失败:\n{err}"))
            self.root.after(0, lambda: self.status_var.set("状态: 语音引擎初始化失败"))
            if com_initialized:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
            return

        self.active_voice = voice
        try:
            selected_voice_id = self.voice_id_var.get().strip()
            if selected_voice_id:
                tokens = voice.GetVoices()
                for i in range(tokens.Count):
                    token = tokens.Item(i)
                    if str(token.Id) == selected_voice_id:
                        voice.Voice = token
                        break

            rate_slider = int(self.rate_var.get())
            sapi_rate = max(-10, min(10, int(round((rate_slider - 180) / 12))))
            voice.Rate = sapi_rate

            volume_slider = float(self.volume_var.get())
            voice.Volume = max(0, min(100, int(round(volume_slider * 100))))
        except Exception:
            pass

        svs_flags_async = 1
        svs_flag_purge = 2
        srs_is_speaking = 2

        total = len(self.current_chunks)
        while self.current_chunk_index < total:
            if self.stop_event.is_set():
                break

            while self.pause_event.is_set() and not self.stop_event.is_set():
                time.sleep(0.1)

            if self.stop_event.is_set():
                break

            chunk = self.current_chunks[self.current_chunk_index]
            now = self.current_chunk_index + 1

            self.root.after(
                0,
                lambda a=now, b=total: self.status_var.set(
                    f"状态: 正在朗读（第 {a}/{b} 段）"
                ),
            )

            try:
                voice.Speak(chunk, svs_flags_async)
                while True:
                    if self.stop_event.is_set():
                        try:
                            voice.Speak("", svs_flag_purge)
                        except Exception:
                            pass
                        break

                    if self.pause_event.is_set():
                        try:
                            voice.Pause()
                        except Exception:
                            pass
                        while self.pause_event.is_set() and not self.stop_event.is_set():
                            time.sleep(0.1)
                        try:
                            voice.Resume()
                        except Exception:
                            pass

                    try:
                        running_state = int(voice.Status.RunningState)
                    except Exception:
                        running_state = 0

                    if running_state != srs_is_speaking:
                        break
                    time.sleep(0.05)
            except Exception as e:
                self.root.after(
                    0,
                    lambda err=e: messagebox.showerror(
                        "语音引擎错误", f"朗读时发生错误:\n{err}"
                    ),
                )
                break

            if self.stop_event.is_set():
                break
            self.current_chunk_index += 1

        if self.stop_event.is_set():
            self.root.after(0, lambda: self.status_var.set("状态: 已停止"))
        else:
            self.root.after(0, lambda: self.status_var.set("状态: 朗读完成"))

        self.active_voice = None
        try:
            voice.Speak("", svs_flag_purge)
        except Exception:
            pass
        if com_initialized:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    def pause_read(self):
        if self.reader_thread and self.reader_thread.is_alive():
            self.pause_event.set()
            self.status_var.set("状态: 已暂停")

    def resume_read(self):
        if self.reader_thread and self.reader_thread.is_alive():
            self.pause_event.clear()
            self.status_var.set("状态: 继续朗读")

    def stop_read(self):
        self.stop_event.set()
        self.pause_event.clear()

        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=0.8)

        self.reader_thread = None
        self.current_chunk_index = 0

    def on_close(self):
        self.stop_read()
        self.root.destroy()


if __name__ == "__main__":
    app_root = tk.Tk()
    ReaderApp(app_root)
    app_root.mainloop()
