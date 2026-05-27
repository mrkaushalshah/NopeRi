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
  searchMode = 'development';
  isSearching = false;
  searchError = '';

  // Data state
  companies: Company[] = [];
  stats: PipelineStats = { discovered: 0, website_found: 0, email_found: 0, drafted: 0, sent: 0 };
  savedLocations: string[] = [];

  // UI state
  activeFilter = 'all';
  isLoaded = false;
  searchQuery = '';
  currentPage = 1;
  itemsPerPage = 10;

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

    this.api.searchCompanies(loc, this.searchRadius, this.searchMode).subscribe({
      next: (res) => {
        // Reload full company list right away in case we already have some data
        this.api.getCompanies(loc).subscribe({
          next: (dbRes) => {
            this.companies = dbRes.companies;
            this.stats = dbRes.stats;
            this.currentPage = 1; // reset pagination
          }
        });

        // Start polling for updates every 5s while search is running
        this.pollInterval = setInterval(() => {
          this.api.checkSearchStatus(loc).subscribe(status => {
            if (!status.is_searching) {
              clearInterval(this.pollInterval);
              this.isSearching = false;
            }
            // Fetch latest DB state
            this.api.getCompanies(loc).subscribe({
              next: (latest) => {
                this.companies = latest.companies;
                this.stats = latest.stats;
              }
            });
          });
        }, 5000);
      },
      error: (err) => {
        this.searchError = err.error?.detail || 'Search failed to start';
        this.isSearching = false;
      }
    });
  }

  filterByLocation(loc: string) {
    this.searchLocation = loc;
    this.api.getCompanies(loc).subscribe({
      next: (res) => {
        this.companies = res.companies;
        this.stats = res.stats;
        this.currentPage = 1;
      }
    });
  }

  showAll() {
    this.searchLocation = '';
    this.loadExistingData();
    this.currentPage = 1;
  }

  get filteredCompanies(): Company[] {
    let filtered = this.companies;
    
    // Apply status filter
    if (this.activeFilter !== 'all') {
      filtered = filtered.filter(c => {
        switch (this.activeFilter) {
          case 'ready': return c.status === 'outreach_ready';
          case 'high-score': return (c.fit_score || 0) >= 70;
          case 'with-email': return c.outreach_emails?.some(e => e.email_subject);
          case 'sent': return c.status === 'sent_manually';
          default: return true;
        }
      });
    }

    // Apply search query filter
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase().trim();
      filtered = filtered.filter(c => 
        c.name?.toLowerCase().includes(q) || 
        c.address?.toLowerCase().includes(q) ||
        c.website?.toLowerCase().includes(q)
      );
    }
    
    return filtered;
  }

  get paginatedCompanies(): Company[] {
    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    return this.filteredCompanies.slice(startIndex, startIndex + this.itemsPerPage);
  }
  
  get totalPages(): number {
    return Math.ceil(this.filteredCompanies.length / this.itemsPerPage);
  }

  nextPage() {
    if (this.currentPage < this.totalPages) this.currentPage++;
  }

  prevPage() {
    if (this.currentPage > 1) this.currentPage--;
  }

  onStatusChanged() {
    this.api.getCompanies(this.searchLocation || undefined).subscribe({
      next: (res) => {
        this.stats = res.stats;
      }
    });
  }

  onCompanyDeleted(companyId: string) {
    this.companies = this.companies.filter(c => c.id !== companyId);
    this.onStatusChanged();
  }

  get funnelPercentage(): number {
    if (!this.stats.discovered) return 0;
    return Math.round((this.stats.drafted / this.stats.discovered) * 100);
  }
}
