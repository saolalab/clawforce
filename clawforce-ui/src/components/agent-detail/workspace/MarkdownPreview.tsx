import { marked } from "marked";
import DOMPurify from "dompurify";

marked.setOptions({ breaks: true, gfm: true });

export function MarkdownPreview({ content }: { content: string }) {
  const html = DOMPurify.sanitize(marked.parse(content) as string);
  return (
    <div
      className="prose prose-sm max-w-none overflow-y-auto p-6 h-full
        prose-headings:text-claude-text-primary prose-p:text-claude-text-secondary
        prose-a:text-claude-accent prose-code:text-claude-accent prose-code:bg-claude-surface
        prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:before:content-none prose-code:after:content-none
        prose-pre:bg-claude-bg prose-pre:border prose-pre:border-claude-border prose-pre:rounded-lg
        prose-blockquote:border-claude-accent prose-blockquote:text-claude-text-muted
        prose-strong:text-claude-text-primary prose-li:text-claude-text-secondary
        prose-hr:border-claude-border
        prose-table:text-sm prose-th:text-claude-text-primary prose-td:text-claude-text-secondary
        prose-th:border-claude-border prose-td:border-claude-border"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
