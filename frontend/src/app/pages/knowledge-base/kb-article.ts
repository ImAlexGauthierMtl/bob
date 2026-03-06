import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DatePipe } from '@angular/common';

import {
    KnowledgeBaseService,
    KBArticle,
    KBArticleSummary,
} from '../../shared/services/kb.service';

interface TocEntry {
    id: string;
    text: string;
    level: number;
}

@Component({
    selector: 'app-kb-article',
    standalone: true,
    imports: [RouterLink, DatePipe],
    templateUrl: './kb-article.html',
    styleUrl: './kb-article.css',
})
export class KBArticleComponent implements OnInit {
    article: KBArticle | null = null;
    relatedArticles: KBArticleSummary[] = [];
    toc: TocEntry[] = [];
    renderedContent = '';
    feedbackGiven = false;

    constructor(
        private route: ActivatedRoute,
        private kbService: KnowledgeBaseService,
    ) { }

    ngOnInit(): void {
        this.route.params.subscribe((params) => {
            const slug = params['slug'];
            if (slug) this.loadArticle(slug);
        });
    }

    loadArticle(slug: string): void {
        this.kbService.getArticle(slug).subscribe({
            next: (article) => {
                this.article = article;
                this.processContent(article.content || '');
                this.loadRelated();
            },
        });
    }

    loadRelated(): void {
        if (!this.article) return;
        this.kbService
            .listArticles({ category_id: this.article.category_id || undefined, limit: 4 })
            .subscribe({
                next: (res) => {
                    this.relatedArticles = res.items.filter(
                        (a) => a.id !== this.article!.id
                    ).slice(0, 2);
                },
            });
    }

    processContent(markdown: string): void {
        // Simple markdown → HTML conversion (headings, paragraphs, lists, code, bold, links, images)
        const lines = markdown.split('\n');
        const htmlParts: string[] = [];
        const tocEntries: TocEntry[] = [];
        let inList = false;
        let tocIndex = 0;

        for (const line of lines) {
            const trimmed = line.trim();

            // Headings
            const headingMatch = trimmed.match(/^(#{1,3})\s+(.+)/);
            if (headingMatch) {
                if (inList) { htmlParts.push('</ul>'); inList = false; }
                const level = headingMatch[1].length;
                const text = headingMatch[2];
                const id = `section-${tocIndex++}`;
                tocEntries.push({ id, text, level });
                htmlParts.push(`<h${level + 1} id="${id}" class="article__heading article__heading--${level}">${this.escapeHtml(text)}</h${level + 1}>`);
                continue;
            }

            // List items
            if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                if (!inList) { htmlParts.push('<ul class="article__list">'); inList = true; }
                htmlParts.push(`<li>${this.inlineMarkdown(trimmed.slice(2))}</li>`);
                continue;
            }

            if (inList) { htmlParts.push('</ul>'); inList = false; }

            // Empty line
            if (!trimmed) {
                continue;
            }

            // Block quote / callout
            if (trimmed.startsWith('> ')) {
                htmlParts.push(`<blockquote class="article__callout">${this.inlineMarkdown(trimmed.slice(2))}</blockquote>`);
                continue;
            }

            // Standalone image line: ![alt](url)
            const imgMatch = trimmed.match(/^!\[(.*)\]\((.+?)\)$/);
            if (imgMatch) {
                const alt = imgMatch[1];
                const src = imgMatch[2];
                htmlParts.push(
                    `<figure class="article__figure">` +
                    `<img src="${src}" alt="${this.escapeHtml(alt)}" class="article__image" loading="lazy" />` +
                    (alt ? `<figcaption class="article__figcaption">${this.escapeHtml(alt)}</figcaption>` : '') +
                    `</figure>`
                );
                continue;
            }

            // Regular paragraph
            htmlParts.push(`<p class="article__paragraph">${this.inlineMarkdown(trimmed)}</p>`);
        }

        if (inList) htmlParts.push('</ul>');

        this.toc = tocEntries;
        this.renderedContent = htmlParts.join('\n');
    }

    inlineMarkdown(text: string): string {
        let html = this.escapeHtml(text);
        // Bold
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        // Italic
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        // Inline code
        html = html.replace(/`(.+?)`/g, '<code class="article__code">$1</code>');
        // Inline images (must come before links)
        html = html.replace(/!\[(.+?)\]\((.+?)\)/g, '<img src="$2" alt="$1" class="article__image--inline" loading="lazy" />');
        // Links
        html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" class="article__link">$1</a>');
        return html;
    }

    escapeHtml(text: string): string {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    sendFeedback(helpful: boolean): void {
        if (!this.article || this.feedbackGiven) return;
        this.feedbackGiven = true;
        this.kbService.sendFeedback(this.article.id, helpful).subscribe({
            next: (res) => {
                if (this.article) {
                    this.article.helpful_yes = res.helpful_yes;
                    this.article.helpful_no = res.helpful_no;
                }
            },
        });
    }

    scrollToSection(id: string): void {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    getVisibilityLabel(v: string): string {
        return v === 'internal' ? 'Internal' : v === 'shared' ? 'Shared' : 'Public';
    }

    getVisibilityClass(v: string): string {
        return v === 'internal' ? 'badge--internal' : v === 'shared' ? 'badge--shared' : 'badge--public';
    }
}
