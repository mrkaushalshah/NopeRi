import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Company, ApiService } from '../services/api';

@Component({
  selector: '[app-company-card]',
  imports: [CommonModule],
  templateUrl: './company-card.html',
  styleUrl: './company-card.css',
})
export class CompanyCard {
  @Input() company!: Company;
  @Output() statusChanged = new EventEmitter<void>();

  copiedField: string | null = null;
  isUpdating = false;

  constructor(private api: ApiService) {}

  markAsSent() {
    this.isUpdating = true;
    this.api.updateCompanyStatus(this.company.id, 'sent_manually').subscribe({
      next: () => {
        this.company.status = 'sent_manually';
        this.isUpdating = false;
        this.statusChanged.emit();
      },
      error: () => {
        this.isUpdating = false;
      }
    });
  }

  get emails(): string[] {
    if (!this.company.outreach_emails?.length) return [];
    try {
      const raw = this.company.outreach_emails[0]?.extracted_emails;
      if (!raw) return [];
      return typeof raw === 'string' ? JSON.parse(raw) : raw;
    } catch {
      return [];
    }
  }

  get emailSubject(): string {
    return this.company.outreach_emails?.[0]?.email_subject || '';
  }

  get emailBody(): string {
    return this.company.outreach_emails?.[0]?.email_body || '';
  }

  get scoreClass(): string {
    const score = this.company.fit_score || 0;
    if (score >= 70) return 'score-high';
    if (score >= 40) return 'score-mid';
    return 'score-low';
  }

  get scoreLabel(): string {
    const score = this.company.fit_score || 0;
    if (score >= 70) return 'Strong Fit';
    if (score >= 40) return 'Moderate';
    return 'Low Fit';
  }

  get statusIcon(): string {
    switch (this.company.status) {
      case 'outreach_ready': return '✉️';
      case 'sent_manually': return '✅';
      case 'responded': return '🎉';
      case 'email_found': return '📧';
      case 'website_found': return '🌐';
      case 'skipped': return '⏭️';
      default: return '🔍';
    }
  }

  get statusLabel(): string {
    return (this.company.status || 'discovered').replace(/_/g, ' ');
  }

  get intelligenceCard(): any {
    if (this.company.intelligence_card) return this.company.intelligence_card;
    if (this.company.intelligence_card_json) {
      try {
        return JSON.parse(this.company.intelligence_card_json);
      } catch {
        return {};
      }
    }
    return {};
  }

  get ratingStars(): string {
    const rating = this.company.google_rating || 0;
    const full = Math.floor(rating);
    const half = rating % 1 >= 0.5 ? 1 : 0;
    return '★'.repeat(full) + (half ? '½' : '') + '☆'.repeat(5 - full - half);
  }

  async copyToClipboard(text: string, field: string) {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      this.copiedField = field;
      setTimeout(() => {
        this.copiedField = null;
      }, 2000);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  }

  openWebsite() {
    if (this.company.website) {
      let url = this.company.website;
      if (!url.startsWith('http')) url = 'https://' + url;
      window.open(url, '_blank');
    }
  }

  openGoogleMaps() {
    const query = encodeURIComponent(this.company.name + ' ' + (this.company.address || ''));
    window.open(`https://www.google.com/maps/search/?api=1&query=${query}`, '_blank');
  }
}
