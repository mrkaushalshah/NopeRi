import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Company {
  id: string;
  name: string;
  location: string;
  address: string;
  distance_km: number;
  website: string;
  google_rating: number;
  google_place_id: string;
  fit_score: number;
  fit_reasoning: string;
  intelligence_card_json: string;
  intelligence_card: any;
  status: string;
  search_location: string;
  search_radius: number;
  created_at: string;
  outreach_emails: OutreachEmail[];
}

export interface OutreachEmail {
  id: string;
  company_id: string;
  extracted_emails: string;
  email_subject: string;
  email_body: string;
  sent_status: string;
  created_at: string;
}

export interface PipelineStats {
  discovered: number;
  website_found: number;
  email_found: number;
  drafted: number;
  sent: number;
}

export interface SearchResponse {
  status: string;
  location: string;
  radius: number;
  total_found: number;
  saved: number;
  pipeline_stats: PipelineStats;
}

export interface CompaniesResponse {
  companies: Company[];
  stats: PipelineStats;
  total: number;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) {}

  searchCompanies(location: string, radius: number, mode: string = 'development'): Observable<SearchResponse> {
    const params = new HttpParams()
      .set('location', location)
      .set('radius', radius.toString())
      .set('mode', mode);
    return this.http.get<SearchResponse>(`${this.baseUrl}/search`, { params });
  }

  checkSearchStatus(location: string): Observable<{ is_searching: boolean }> {
    const params = new HttpParams().set('location', location);
    return this.http.get<{ is_searching: boolean }>(`${this.baseUrl}/search/status`, { params });
  }

  getCompanies(location?: string): Observable<CompaniesResponse> {
    let params = new HttpParams();
    if (location) {
      params = params.set('location', location);
    }
    return this.http.get<CompaniesResponse>(`${this.baseUrl}/companies`, { params });
  }

  updateCompanyStatus(companyId: string, status: string): Observable<any> {
    return this.http.patch(`${this.baseUrl}/companies/${companyId}/status`, { status });
  }

  getCompany(companyId: string): Observable<Company> {
    return this.http.get<Company>(`${this.baseUrl}/companies/${companyId}`);
  }

  deleteCompany(companyId: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/companies/${companyId}`);
  }


  updateEmailStatus(emailId: string, sentStatus: string): Observable<any> {
    return this.http.put(`${this.baseUrl}/emails/${emailId}/status`, { sent_status: sentStatus });
  }

  getStats(location?: string): Observable<PipelineStats> {
    let params = new HttpParams();
    if (location) {
      params = params.set('location', location);
    }
    return this.http.get<PipelineStats>(`${this.baseUrl}/stats`, { params });
  }

  getLocations(): Observable<{ locations: string[] }> {
    return this.http.get<{ locations: string[] }>(`${this.baseUrl}/locations`);
  }
}
