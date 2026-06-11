import { Component, Input, Output, EventEmitter, ChangeDetectorRef, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Company, ApiService } from '../services/api';

@Component({
  selector: '[app-company-card]',
  imports: [CommonModule],
  templateUrl: './company-card.html',
  styleUrl: './company-card.css',
})
export class CompanyCard implements OnInit, OnChanges {
  @Input() company!: Company;
  @Input() globalVerifications: { [email: string]: { status: string, score: number } } = {};
  @Output() statusChanged = new EventEmitter<void>();
  @Output() deleted = new EventEmitter<string>();

  copiedField: string | null = null;
  isUpdating = false;
  isDeleting = false;

  latestUpdateText = '';
  isSavingUpdate = false;
  isUpdateSaved = false;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.syncVerifications();
    this.initLatestUpdateText();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['globalVerifications']) {
      this.syncVerifications();
    }
    if (changes['company']) {
      this.initLatestUpdateText();
    }
  }

  initLatestUpdateText() {
    if (this.company?.outreach_emails?.length) {
      this.latestUpdateText = this.company.outreach_emails[0].latest_update || '';
    } else {
      this.latestUpdateText = '';
    }
  }

  syncVerifications() {
    for (const email of this.emails) {
      if (this.globalVerifications && this.globalVerifications[email]) {
        this.emailVerificationStatus[email] = this.globalVerifications[email].status;
        this.emailVerificationScore[email] = this.globalVerifications[email].score;
      }
    }
  }

  onUpdateTextInput(event: Event) {
    const target = event.target as HTMLInputElement;
    this.latestUpdateText = target.value;
  }

  saveLatestUpdate() {
    if (!this.company) return;
    this.isSavingUpdate = true;
    this.isUpdateSaved = false;
    this.cdr.detectChanges();

    if (!this.company.outreach_emails?.length) {
      const payload = {
        extracted_emails: [],
        email_subject: '',
        email_body: '',
        sent_status: 'pending',
        latest_update: this.latestUpdateText
      };
      this.api.createEmail(this.company.id, payload).subscribe({
        next: (res) => {
          this.company.outreach_emails = [{
            id: res.email_id,
            company_id: this.company.id,
            extracted_emails: '[]',
            email_subject: '',
            email_body: '',
            sent_status: 'pending',
            created_at: new Date().toISOString(),
            latest_update: this.latestUpdateText
          }];
          this.isSavingUpdate = false;
          this.isUpdateSaved = true;
          this.statusChanged.emit();
          this.cdr.detectChanges();
          setTimeout(() => {
            this.isUpdateSaved = false;
            this.cdr.detectChanges();
          }, 3000);
        },
        error: (err) => {
          console.error('Failed to create email entry:', err);
          this.isSavingUpdate = false;
          this.cdr.detectChanges();
        }
      });
    } else {
      const emailId = this.company.outreach_emails[0].id;
      this.api.updateEmailLatestUpdate(emailId, this.latestUpdateText).subscribe({
        next: () => {
          this.company.outreach_emails[0].latest_update = this.latestUpdateText;
          this.isSavingUpdate = false;
          this.isUpdateSaved = true;
          this.cdr.detectChanges();
          setTimeout(() => {
            this.isUpdateSaved = false;
            this.cdr.detectChanges();
          }, 3000);
        },
        error: (err) => {
          console.error('Failed to update latest update text:', err);
          this.isSavingUpdate = false;
          this.cdr.detectChanges();
        }
      });
    }
  }

  markAsSent() {
    this.isUpdating = true;
    this.api.updateCompanyStatus(this.company.id, 'sent_manually').subscribe({
      next: () => {
        this.company.status = 'sent_manually';
        if (this.company.outreach_emails?.length) {
          this.company.outreach_emails[0].sent_status = 'sent';
        }
        this.isUpdating = false;
        this.statusChanged.emit();
        this.cdr.detectChanges();
      },
      error: () => {
        this.isUpdating = false;
        this.cdr.detectChanges();
      }
    });
  }

  markAsBounced() {
    this.isUpdating = true;
    this.api.updateCompanyStatus(this.company.id, 'bounced').subscribe({
      next: () => {
        this.company.status = 'bounced';
        if (this.company.outreach_emails?.length) {
          this.company.outreach_emails[0].sent_status = 'bounced';
        }
        this.isUpdating = false;
        this.statusChanged.emit();
        this.cdr.detectChanges();
      },
      error: () => {
        this.isUpdating = false;
        this.cdr.detectChanges();
      }
    });
  }

  deleteEntry() {
    if (confirm(`Are you sure you want to delete ${this.company.name}?`)) {
      this.isDeleting = true;
      this.api.deleteCompany(this.company.id).subscribe({
        next: () => {
          this.isDeleting = false;
          this.deleted.emit(this.company.id);
          this.cdr.detectChanges();
        },
        error: () => {
          this.isDeleting = false;
          this.cdr.detectChanges();
        }
      });
    }
  }

  emailVerificationStatus: { [email: string]: string } = {};
  emailVerificationScore: { [email: string]: number } = {};

  verifyEmail(email: string, event: Event) {
    event.stopPropagation();
    if (this.emailVerificationStatus[email] === 'verifying') return;
    
    this.emailVerificationStatus[email] = 'verifying';
    this.cdr.detectChanges();

    this.api.verifyEmail(email).subscribe({
      next: (res) => {
        this.emailVerificationStatus[email] = res.status;
        this.emailVerificationScore[email] = res.score || 0;
        
        // Also update the global state so it persists if component is recreated
        if (this.globalVerifications) {
            this.globalVerifications[email] = { status: res.status, score: res.score || 0 };
        }
        
        this.cdr.detectChanges();
      },
      error: () => {
        this.emailVerificationStatus[email] = 'unknown';
        this.cdr.detectChanges();
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
      case 'bounced': return '❌';
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

  openInZohoMail() {
    if (!this.emails.length) return;
    
    // Open Zoho Mail with a hash identifying the company for our assistant script
    const zohoUrl = `https://mail.zoho.com/zm/#noperi-company-id=${this.company.id}`;
    window.open(zohoUrl, '_blank');
  }
}
