import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Company, PipelineStats } from '../services/api';
import { CompanyCard } from '../company-card/company-card';

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, FormsModule, CompanyCard],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard implements OnInit, OnDestroy {
  // Search state
  searchLocation = '';
  searchRadius = 10;
  isSearching = false;
  searchError = '';

  // Data state
  companies: Company[] = [];
  stats: PipelineStats = { discovered: 0, website_found: 0, email_found: 0, drafted: 0, sent: 0 };
  savedLocations: string[] = [];

  // UI state
  activeFilter = 'all';
  isLoaded = false;

  constructor(private api: ApiService) { }

  ngOnInit() {
    this.loadExistingData();
    this.loadLocations();
  }

  loadExistingData() {
    this.api.getCompanies().subscribe({
      next: (res) => {
        this.companies = res.companies;
        this.stats = res.stats;
        this.isLoaded = true;
      },
      error: (err) => {
        console.error('Failed to load companies:', err);
        this.isLoaded = true;
      }
    });
  }

  loadLocations() {
    this.api.getLocations().subscribe({
      next: (res) => {
        this.savedLocations = res.locations;
      },
      error: () => { }
    });
  }

  pollInterval: any;

  ngOnDestroy() {
    if (this.pollInterval) clearInterval(this.pollInterval);
  }

  onSearch() {
    if (!this.searchLocation.trim()) return;

    this.isSearching = true;
    this.searchError = '';
    const loc = this.searchLocation.trim();

    this.api.searchCompanies(loc, this.searchRadius).subscribe({
      next: (res) => {
        // Reload full company list right away in case we already have some data
        this.api.getCompanies(loc).subscribe({
          next: (compRes) => {
            this.companies = compRes.companies;
            this.stats = compRes.stats;
          }
        });

        // Start polling for new data
        this.pollInterval = setInterval(() => {
          this.api.getCompanies(loc).subscribe(compRes => {
            this.companies = compRes.companies;
            this.stats = compRes.stats;
          });

          this.api.checkSearchStatus(loc).subscribe(statusRes => {
            if (!statusRes.is_searching) {
              clearInterval(this.pollInterval);
              this.isSearching = false;
              this.loadLocations();
            }
          });
        }, 5000); // Poll every 5 seconds
      },
      error: (err) => {
        this.isSearching = false;
        this.searchError = err.error?.detail || 'Search failed. Check your API key and try again.';
      }
    });
  }

  filterByLocation(location: string) {
    this.searchLocation = location;
    this.api.getCompanies(location).subscribe({
      next: (res) => {
        this.companies = res.companies;
        console.log(this.companies)
        this.stats = res.stats;
      }
    });
  }

  showAll() {
    this.searchLocation = '';
    this.loadExistingData();
  }

  get filteredCompanies(): Company[] {
    if (this.activeFilter === 'all') return this.companies;
    return this.companies.filter(c => {
      switch (this.activeFilter) {
        case 'ready': return c.status === 'outreach_ready';
        case 'high-score': return (c.fit_score || 0) >= 70;
        case 'with-email': return c.outreach_emails?.some(e => e.email_subject);
        case 'sent': return c.status === 'sent_manually';
        default: return true;
      }
    });
  }

  get funnelPercentage(): number {
    if (!this.stats.discovered) return 0;
    return Math.round((this.stats.drafted / this.stats.discovered) * 100);
  }
}
