"""
AutoLabeler 文档对话框
显示用户使用手册
"""

from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton
from PySide6.QtCore import Qt


class DocsDialog(QDialog):
    """
    文档显示对话框
    显示 Markdown 格式的使用手册（非模态）
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用文档 - AutoLabeler")
        self.resize(900, 700)

        # 获取文档路径（支持打包后的 exe）
        import sys
        if getattr(sys, 'frozen', False):
            # 打包后的 exe，文件在临时目录
            base_path = Path(sys._MEIPASS)
        else:
            # 开发环境
            base_path = Path(__file__).parent.parent.parent
        self.docs_path = base_path / "USER_GUIDE.md"

        self._init_ui()
        self._load_docs()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 设置对话框背景色为白色
        self.setStyleSheet("QDialog { background-color: #ffffff; }")

        # 文档浏览器
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        # 设置浏览器背景色为白色
        self.browser.setStyleSheet("QTextBrowser { background-color: #ffffff; border: none; }")
        layout.addWidget(self.browser)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _load_docs(self):
        """加载文档内容"""
        if not self.docs_path.exists():
            self.browser.setHtml("<h2>文档文件未找到</h2><p>请确保 USER_GUIDE.md 文件存在于项目根目录下。</p>")
            return

        try:
            content = self.docs_path.read_text(encoding='utf-8')
            # 转换 Markdown 为 HTML
            html = self._markdown_to_html(content)
            self.browser.setHtml(html)
        except Exception as e:
            self.browser.setHtml(f"<h2>读取文档失败</h2><p>错误: {str(e)}</p>")

    def _markdown_to_html(self, md_content: str) -> str:
        """
        简单的 Markdown 转 HTML
        仅支持常用语法，简化渲染
        """
        lines = md_content.split('\n')
        html_lines = []
        in_code_block = False
        in_table = False
        code_buffer = []

        for line in lines:
            # 跳过空行（但在某些上下文中保留）
            if not line.strip() and not in_code_block:
                continue

            # 代码块处理
            if line.strip().startswith('```'):
                if in_code_block:
                    # 结束代码块
                    code = '\n'.join(code_buffer)
                    html_lines.append(f'<pre><code>{self._escape_html(code)}</code></pre>')
                    code_buffer = []
                    in_code_block = False
                else:
                    # 开始代码块
                    in_code_block = True
                continue

            if in_code_block:
                code_buffer.append(line)
                continue

            # 标题处理
            if line.startswith('### '):
                html_lines.append(f'<h3>{line[4:].strip()}</h3>')
                continue
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:].strip()}</h2>')
                continue
            elif line.startswith('# '):
                html_lines.append(f'<h1>{line[2:].strip()}</h1>')
                continue

            # 表格处理（简化）
            if '|' in line and line.strip().startswith('|'):
                if '---' not in line:
                    cells = [cell.strip() for cell in line.split('|')[1:-1]]
                    if not in_table:
                        html_lines.append('<table>')
                        in_table = True
                    tag = 'th' if html_lines[-1].endswith('<table>') else 'td'
                    if tag == 'th':
                        html_lines.append('<tr>' + ''.join(f'<{tag}>{self._escape_html(cell)}</{tag}>' for cell in cells) + '</tr>')
                continue
            elif in_table:
                html_lines.append('</table>')
                in_table = False

            # 列表处理
            if line.strip().startswith('- '):
                html_lines.append(f'<ul><li>{self._format_inline(line.strip()[2:])}</li></ul>')
                continue

            # 分隔线
            if line.strip() == '---':
                html_lines.append('<hr>')
                continue

            # 粗体
            line = self._format_inline(line)

            # 普通段落
            if line.strip():
                html_lines.append(f'<p>{line}</p>')

        # 闭合未闭合的标签
        if in_table:
            html_lines.append('</table>')

        # 组合HTML
        html = '\n'.join(html_lines)

        # 添加简洁样式
        style = """
        <style>
            body {
                font-family: "Microsoft YaHei UI", sans-serif;
                padding: 16px;
                background-color: #ffffff;
                color: #000000;
                line-height: 1.6;
                font-size: 14px;
            }
            h1 {
                font-size: 18px;
                font-weight: bold;
                color: #000000;
                margin: 16px 0 8px 0;
            }
            h2 {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
                margin: 14px 0 6px 0;
            }
            h3 {
                font-size: 15px;
                font-weight: bold;
                color: #555555;
                margin: 12px 0 6px 0;
            }
            p {
                margin: 6px 0;
                color: #000000;
                font-size: 14px;
            }
            code {
                background-color: #f0f0f0;
                color: #cc0000;
                padding: 2px 5px;
                font-family: Consolas, monospace;
                font-size: 13px;
            }
            pre {
                background-color: #f5f5f5;
                padding: 12px;
                margin: 12px 0;
                overflow-x: auto;
                font-family: Consolas, monospace;
                font-size: 13px;
                border-radius: 4px;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 12px 0;
                font-size: 14px;
            }
            th, td {
                border: 1px solid #ccc;
                padding: 6px 10px;
                text-align: left;
            }
            th {
                background-color: #f0f0f0;
                font-weight: bold;
            }
            blockquote {
                border-left: 3px solid #ccc;
                padding-left: 12px;
                margin: 12px 0;
                color: #555;
            }
            ul {
                margin: 6px 0;
                padding-left: 20px;
            }
            li {
                margin: 3px 0;
                color: #000000;
                font-size: 14px;
            }
            hr {
                border: none;
                border-top: 1px solid #ddd;
                margin: 16px 0;
            }
            a {
                color: #0066cc;
                text-decoration: underline;
            }
            strong {
                font-weight: bold;
                color: #000000;
            }
        </style>
        """

        return f"<html><head>{style}</head><body>{html}</body></html>"

    def _format_inline(self, text: str) -> str:
        """格式化行内元素"""
        import re
        # 粗体
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        # 行内代码
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        return self._escape_html(text)

    def _escape_html(self, text: str) -> str:
        """转义HTML特殊字符"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;'))
