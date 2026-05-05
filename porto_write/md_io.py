import logging
import mistune
from porto_write.document import PortoDocument, Chapter, TextBlock

logger = logging.getLogger(__name__)

def export_md(doc: PortoDocument, file_path: str):
    """Export a PortoDocument to a Markdown file."""
    lines = []
    
    for chapter in doc.chapters:
        if chapter.title:
            lines.append(f"# {chapter.title}\n")
            
        for block in chapter.blocks:
            if block.style_name == "ChapterHeader":
                # If it's a header block but not the main chapter title
                lines.append(f"# {block.text}\n")
            elif block.style_name == "SubHeader":
                lines.append(f"## {block.text}\n")
            elif block.style_name == "BlockQuote":
                lines.append(f"> {block.text}\n")
            else:
                # Body or other styles
                lines.append(f"{block.text}\n")
        
        # Add extra newline between chapters
        lines.append("\n")
        
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("".join(lines))
    
    logger.info("Exported Markdown to %s", file_path)

def import_md(file_path: str) -> PortoDocument:
    """Import a Markdown file into a PortoDocument."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
        
    markdown = mistune.create_markdown(renderer='ast')
    ast = markdown(text)
    
    doc = PortoDocument()
    current_chapter = None
    
    for node in ast:
        node_type = node.get("type")
        
        if node_type == "heading":
            attrs = node.get("attrs", {})
            level = attrs.get("level")
            content = _get_text_from_node(node)
            
            if level == 1:
                current_chapter = doc.add_chapter(content)
            elif level == 2:
                if not current_chapter:
                    current_chapter = doc.add_chapter("Chapter")
                current_chapter.add_block("SubHeader", content)
            else:
                if not current_chapter:
                    current_chapter = doc.add_chapter("Chapter")
                current_chapter.add_block("Body", content)
                
        elif node_type == "paragraph":
            if not current_chapter:
                current_chapter = doc.add_chapter("Chapter")
            content = _get_text_from_node(node)
            if content:
                current_chapter.add_block("Body", content)
            
        elif node_type == "block_quote":
            if not current_chapter:
                current_chapter = doc.add_chapter("Chapter")
            content = _get_text_from_node(node)
            if content:
                current_chapter.add_block("BlockQuote", content)
            
    logger.info("Imported Markdown from %s", file_path)
    return doc

def _get_text_from_node(node: dict) -> str:
    """Recursively extract text from a mistune AST node."""
    text = ""
    if "text" in node:
        text += node["text"]
    if "raw" in node:
        text += node["raw"]
        
    if "children" in node:
        for child in node["children"]:
            text += _get_text_from_node(child)
            
    return text.strip()
