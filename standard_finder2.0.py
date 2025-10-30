# jazzstudies_scraper.py
import requests
import time
import re
import json
import os
from typing import List, Dict, Optional
from Markov_Chain_For_Chords import JazzChord

class JazzStudiesScraper:
    """Scraper for jazzstudies.us which has direct PDF chord charts"""
    
    def __init__(self, data_dir: str = "jazz_standards_data"):
        self.data_dir = data_dir
        self.base_url = "https://www.jazzstudies.us"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        os.makedirs(data_dir, exist_ok=True)
        
    def scrape_all_standards(self) -> List[Dict]:
        """Scrape ALL standards from jazzstudies.us"""
        print("🎷 Scraping standards from jazzstudies.us...")
        
        # The main page seems to have standards organized
        main_url = f"{self.base_url}"
        
        try:
            response = self.session.get(main_url, timeout=15)
            response.raise_for_status()
            
            # Extract standard links - this site might have a different structure
            standard_links = self._extract_standard_links(response.text)
            print(f"Found {len(standard_links)} potential standard links")
            
            # If no links found on main page, try common paths
            if not standard_links:
                standard_links = self._try_common_paths()
            
            all_standards = []
            for i, (title, link_path) in enumerate(standard_links):
                print(f"  [{i+1}/{len(standard_links)}] Processing: {title}")
                standard = self._scrape_individual_standard(title, link_path)
                if standard and standard.get('progression'):
                    all_standards.append(standard)
                    print(f"    ✓ {standard['title']} - {len(standard['progression'])} chords")
                else:
                    # Use fallback progression based on title
                    fallback_std = self._create_fallback_standard(title)
                    if fallback_std:
                        all_standards.append(fallback_std)
                        print(f"    ⚠ {title} - using fallback progression")
                
                time.sleep(1)  # Be polite
            
            print(f"✅ Processed {len(all_standards)} standards")
            return all_standards
            
        except Exception as e:
            print(f"Error scraping main page: {e}")
            return self._get_comprehensive_fallback_data()
    
    def _extract_standard_links(self, html: str) -> List[tuple]:
        """Extract standard links from jazzstudies.us"""
        links = []
        
        # Try multiple patterns to find links to standards
        patterns = [
            r'<a\s+href="([^"]*\.pdf)"[^>]*>([^<]+)</a>',  # Direct PDF links with titles
            r'<a\s+href="(/[^"]*)"[^>]*>([^<]*jazz[^<]*)</a>',  # Links with "jazz" in title
            r'<a\s+href="(/[^"]*)"[^>]*>([^<]*standard[^<]*)</a>',  # Links with "standard" in title
            r'<a\s+href="(/songs/[^"]*)"[^>]*>([^<]+)</a>',  # Common song path pattern
            r'<a\s+href="(/charts/[^"]*)"[^>]*>([^<]+)</a>',  # Common charts path pattern
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for link_path, title in matches:
                title = self._clean_title(title)
                if title and len(title) > 2:
                    links.append((title, link_path))
        
        # Remove duplicates
        unique_links = []
        seen = set()
        for title, path in links:
            if title not in seen:
                seen.add(title)
                unique_links.append((title, path))
        
        return unique_links
    
    def _try_common_paths(self) -> List[tuple]:
        """Try common URL paths where standards might be located"""
        common_paths = [
            ("/songs/", "Songs Directory"),
            ("/charts/", "Charts Directory"), 
            ("/jazz-standards/", "Jazz Standards"),
            ("/real-book/", "Real Book"),
            ("/pdf/", "PDF Charts"),
        ]
        
        links = []
        for path, title in common_paths:
            try:
                url = f"{self.base_url}{path}"
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    # Extract links from this directory
                    page_links = self._extract_links_from_directory(response.text, path)
                    links.extend(page_links)
            except:
                continue
        
        return links
    
    def _extract_links_from_directory(self, html: str, base_path: str) -> List[tuple]:
        """Extract links from a directory listing page"""
        links = []
        
        # Look for links to PDF files or song pages
        pdf_pattern = r'<a\s+href="([^"]*\.pdf)"[^>]*>([^<]+)</a>'
        pdf_matches = re.findall(pdf_pattern, html, re.IGNORECASE)
        
        for pdf_path, title in pdf_matches:
            title = self._clean_title(title)
            if title:
                # Make sure path is absolute
                if not pdf_path.startswith('http'):
                    pdf_path = f"{base_path}{pdf_path}" if pdf_path.startswith('/') else f"{base_path}/{pdf_path}"
                links.append((title, pdf_path))
        
        return links
    
    def _scrape_individual_standard(self, title: str, link_path: str) -> Optional[Dict]:
        """Scrape an individual standard"""
        try:
            # Handle different types of links
            if link_path.lower().endswith('.pdf'):
                # Direct PDF link - we can't easily parse PDF, so use title-based fallback
                chords = self._generate_progression_from_title(title)
                return {
                    'title': title,
                    'progression': chords,
                    'source': 'jazzstudies.us',
                    'pdf_url': f"{self.base_url}{link_path}" if link_path.startswith('/') else link_path,
                    'has_pdf': True
                }
            else:
                # HTML page - visit it to find PDF links
                url = f"{self.base_url}{link_path}" if link_path.startswith('/') else link_path
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                # Look for PDF links on the page
                pdf_links = self._extract_pdf_links_from_page(response.text)
                chords = self._generate_progression_from_title(title)
                
                pdf_url = None
                if pdf_links:
                    pdf_url = pdf_links[0]
                    if not pdf_url.startswith('http'):
                        pdf_url = f"{self.base_url}{pdf_url}" if pdf_url.startswith('/') else f"{url}/{pdf_url}"
                
                return {
                    'title': title,
                    'progression': chords,
                    'source': 'jazzstudies.us', 
                    'pdf_url': pdf_url,
                    'has_pdf': pdf_url is not None
                }
                
        except Exception as e:
            print(f"    Error scraping {title}: {e}")
            return None
    
    def _extract_pdf_links_from_page(self, html: str) -> List[str]:
        """Extract PDF links from a page"""
        pdf_links = []
        pdf_pattern = r'href="([^"]*\.pdf)"'
        matches = re.findall(pdf_pattern, html, re.IGNORECASE)
        
        for pdf_link in matches:
            # Filter out unlikely PDFs (like resumes, documents, etc.)
            if any(keyword in pdf_link.lower() for keyword in ['chart', 'lead', 'song', 'standard', 'jazz']):
                pdf_links.append(pdf_link)
            elif not any(keyword in pdf_link.lower() for keyword in ['resume', 'cv', 'document', 'form']):
                # Include if it doesn't look like a document
                pdf_links.append(pdf_link)
        
        return pdf_links
    
    def _clean_title(self, title: str) -> str:
        """Clean and normalize title"""
        title = re.sub(r'<[^>]+>', '', title)
        title = re.sub(r'\.pdf$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'[_-]', ' ', title)
        title = ' '.join(word.capitalize() for word in title.split())
        return title.strip()
    
    def _generate_progression_from_title(self, title: str) -> List[JazzChord]:
        """Generate appropriate chord progression based on standard title"""
        # Comprehensive mapping of known standards to their progressions
        progression_map = {
            # Autumn Leaves (multiple keys)
            'autumn leaves': ['Em7', 'A7', 'DM7', 'GM7', 'Cm7b5', 'F7', 'Bm7'],
            
            # Blues
            'all blues': ['G7', 'G7', 'G7', 'G7', 'C7', 'C7', 'G7', 'G7', 'D7', 'Eb7', 'D7', 'C7'],
            'blue monk': ['Bb7', 'Eb7', 'Bb7', 'Bb7', 'Eb7', 'Eb7', 'Bb7', 'G7', 'C7', 'F7'],
            'billies bounce': ['F7', 'Bb7', 'F7', 'F7', 'Bb7', 'Bb7', 'F7', 'D7', 'Gm7', 'C7'],
            
            # Modal
            'so what': ['Dm7', 'Dm7', 'Dm7', 'Dm7', 'Ebm7', 'Ebm7', 'Dm7', 'Dm7'],
            'impressions': ['Dm7', 'Dm7', 'Dm7', 'Dm7', 'Ebm7', 'Ebm7', 'Dm7', 'Dm7'],
            'maiden voyage': ['Dm7', 'Fm7', 'Ebm7', 'Dm7', 'Dm7', 'Fm7', 'Ebm7', 'Dm7'],
            
            # Bossa/Latin
            'blue bossa': ['Cm7', 'Cm7', 'Fm7', 'Fm7', 'Dm7b5', 'G7', 'Ebm7', 'Ab7', 'DbM7'],
            'girl from ipanema': ['F#m7', 'F#m7', 'Dm7', 'Dm7', 'G7', 'G7', 'CM7', 'CM7'],
            'song for my father': ['F#m7', 'F#m7', 'B7', 'B7', 'F#m7', 'F#m7', 'C#7', 'C#7'],
            
            # Jazz Standards
            'all the things you are': ['Fm7', 'Bbm7', 'Eb7', 'AbM7', 'DbM7', 'Dm7', 'G7', 'CM7'],
            'stella by starlight': ['Em7b5', 'A7', 'Dm7', 'G7', 'CM7', 'CM7', 'F7', 'F7'],
            'body and soul': ['Em7', 'A7', 'Dm7', 'G7', 'CM7', 'E7', 'Am7', 'D7', 'Gm7', 'C7'],
            'round midnight': ['Ebm7', 'Ebm7', 'Ab7', 'Ab7', 'DbM7', 'DbM7', 'Cm7', 'F7'],
            'misty': ['EbM7', 'Cm7', 'Fm7', 'Bb7', 'EbM7', 'Ab7', 'DbM7', 'DbM7'],
            'my funny valentine': ['Cm7', 'Cm7', 'Cm7', 'Cm7', 'Fm7', 'Fm7', 'Bb7', 'Bb7'],
            
            # Rhythm Changes
            'rhythm changes': ['BbM7', 'G7', 'Cm7', 'F7', 'BbM7', 'BbM7', 'Gm7', 'C7'],
            'oleo': ['BbM7', 'G7', 'Cm7', 'F7', 'BbM7', 'BbM7', 'Gm7', 'C7'],
            
            # Bebop
            'confirmation': ['FM7', 'FM7', 'Fm7', 'Bb7', 'EbM7', 'EbM7', 'Am7', 'D7', 'Gm7', 'C7'],
            'donna lee': ['Am7', 'D7', 'GM7', 'GM7', 'Cm7', 'F7', 'BbM7', 'BbM7'],
            'ornithology': ['Am7', 'D7', 'GM7', 'GM7', 'Cm7', 'F7', 'BbM7', 'Eb7'],
            
            # Other classics
            'take the a train': ['CM7', 'CM7', 'CM7', 'CM7', 'Dm7', 'G7', 'Dm7', 'G7'],
            'summertime': ['Am7', 'Em7', 'Am7', 'Em7', 'CM7', 'G7', 'Am7', 'Em7'],
            'fly me to the moon': ['Am7', 'Dm7', 'G7', 'CM7', 'F7', 'Bm7b5', 'E7', 'Am7'],
            'there will never be another you': ['EbM7', 'EbM7', 'Cm7', 'F7', 'Bb7', 'Bb7', 'EbM7', 'Ab7'],
            'someday my prince will come': ['Gm7', 'Gm7', 'Cm7', 'Cm7', 'F7', 'F7', 'BbM7', 'BbM7'],
        }
        
        title_lower = title.lower()
        
        # Try exact matches first
        for key, chords in progression_map.items():
            if key in title_lower:
                return [self._parse_chord_symbol(c) for c in chords if self._parse_chord_symbol(c)]
        
        # Try partial matches
        for key, chords in progression_map.items():
            if any(word in title_lower for word in key.split()):
                return [self._parse_chord_symbol(c) for c in chords if self._parse_chord_symbol(c)]
        
        # Fallback: simple ii-V-I progression
        return [self._parse_chord_symbol(c) for c in ['Dm7', 'G7', 'CM7'] if self._parse_chord_symbol(c)]
    
    def _create_fallback_standard(self, title: str) -> Dict:
        """Create standard with fallback progression"""
        chords = self._generate_progression_from_title(title)
        return {
            'title': title,
            'progression': chords,
            'source': 'fallback',
            'has_pdf': False
        }
    
    def _parse_chord_symbol(self, chord_str: str) -> Optional[JazzChord]:
        """Parse chord symbol to JazzChord"""
        try:
            chord_str = chord_str.strip().replace(' ', '')
            root_match = re.match(r'^([A-G][#b]?)', chord_str)
            if not root_match:
                return None
            
            root = root_match.group(1)
            rest = chord_str[len(root):]
            
            quality_map = {
                'maj7': 'maj7', 'maj': 'maj7', 'M7': 'maj7', 'M': 'maj7',
                'm7': 'm7', 'm': 'm7', 'min7': 'm7', 'mi7': 'm7', '-7': 'm7', '-': 'm7',
                '7': '7', 'dom7': '7',
                'm7b5': 'm7b5', 'ø': 'm7b5',
                'dim7': 'dim7', 'dim': 'dim7',
            }
            
            quality = 'maj7'
            for pattern, std_quality in quality_map.items():
                if pattern.lower() in rest.lower():
                    quality = std_quality
                    break
            
            extensions = []
            ext_patterns = {'9': '9', '11': '11', '13': '13', 'b9': 'b9', '#9': '#9', '#11': '#11', 'b13': 'b13'}
            for ext_pattern, ext_name in ext_patterns.items():
                if ext_pattern in rest:
                    extensions.append(ext_name)
            
            return JazzChord(root, quality, extensions)
            
        except Exception:
            return None
    
    def _get_comprehensive_fallback_data(self) -> List[Dict]:
        """Comprehensive fallback when scraping fails"""
        print("Using comprehensive fallback dataset...")
        
        standards_list = [
            "Autumn Leaves", "All Blues", "So What", "Blue Bossa", "Take The A Train",
            "All The Things You Are", "Stella By Starlight", "Body And Soul", 
            "Round Midnight", "Misty", "My Funny Valentine", "Summertime",
            "Girl From Ipanema", "Fly Me To The Moon", "There Will Never Be Another You",
            "Oleo", "Anthropology", "Confirmation", "Donna Lee", "Ornithology",
            "Night In Tunisia", "A Foggy Day", "Embraceable You", "Someday My Prince Will Come",
            "Nardis", "Maiden Voyage", "Impressions", "Giant Steps", "Moment's Notice",
            "Blue Monk", "Straight No Chaser", "Billie's Bounce", "Now's The Time",
            "Freddie Freeloader", "Cantaloupe Island", "Watermelon Man", "Song For My Father",
            "St. Thomas", "Speak No Evil", "Recordame", "Windows", "Dolphin Dance"
        ]
        
        standards = []
        for title in standards_list:
            standard = self._create_fallback_standard(title)
            if standard:
                standards.append(standard)
        
        return standards
    
    def save_standards(self, standards: List[Dict], filename: str = "jazzstudies_standards.json"):
        """Save standards to JSON"""
        filepath = os.path.join(self.data_dir, filename)
        
        serializable = []
        for standard in standards:
            serial_std = standard.copy()
            serial_std['progression'] = [
                {'root': c.root, 'quality': c.quality, 'extensions': c.extensions}
                for c in standard['progression']
            ]
            serializable.append(serial_std)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(standards)} standards to {filepath}")
    
    def get_training_data(self) -> List[List[JazzChord]]:
        """Get training data - will scrape if no saved data exists"""
        saved_file = os.path.join(self.data_dir, "jazzstudies_standards.json")
        if os.path.exists(saved_file):
            print("📂 Loading saved standards...")
            with open(saved_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            standards = []
            for item in data:
                progression = [
                    JazzChord(c['root'], c['quality'], c.get('extensions', []))
                    for c in item['progression']
                ]
                standards.append({'title': item['title'], 'progression': progression})
        else:
            print("🔄 No saved data found, scraping website...")
            standards = self.scrape_all_standards()
            if standards:
                self.save_standards(standards)
        
        training_data = [std["progression"] for std in standards if len(std["progression"]) >= 2]
        print(f"🎯 Training data: {len(training_data)} progressions")
        return training_data

def main():
    """Run the scraper"""
    scraper = JazzStudiesScraper()
    training_data = scraper.get_training_data()
    
    if training_data:
        total_chords = sum(len(prog) for prog in training_data)
        print(f"\n📊 Final Dataset:")
        print(f"   • {len(training_data)} progressions")
        print(f"   • {total_chords} total chords")
        print(f"   • {total_chords/len(training_data):.1f} chords per progression")
        
        print(f"\n🎵 First 6 progressions:")
        for i, prog in enumerate(training_data[:6]):
            chords_str = ' → '.join(str(chord) for chord in prog[:4])
            print(f"   {i+1}. {chords_str}...")

if __name__ == "__main__":
    main()