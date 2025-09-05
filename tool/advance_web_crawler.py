import requests
from bs4 import BeautifulSoup
import re
import tldextract
from urllib.parse import urljoin, urlparse, urlunparse
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
from collections import deque
import random
import csv
from datetime import datetime
from urllib.robotparser import RobotFileParser
import urllib3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from threading import Thread
import queue
import os
import sys
import ssl
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import subprocess

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Create a custom SSL context to avoid certificate verification issues
ssl._create_default_https_context = ssl._create_unverified_context

class AdvancedWebCrawler:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Web Crawler")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # Configuration with defaults
        self.base_url = tk.StringVar(value="https://digitalnexgen.org")
        self.max_depth = tk.IntVar(value=2)
        self.delay = tk.DoubleVar(value=1.0)
        self.timeout = tk.IntVar(value=10)
        self.max_threads = tk.IntVar(value=5)
        
        # Results directory
        self.results_dir = tk.StringVar(value=os.path.join(os.getcwd(), "crawl_results"))
        
        # Data structures
        self.visited = set()
        self.all_links = set()
        self.subdomain_links = set()
        self.external_links = set()
        self.broken_links = set()
        self.hidden_paths = set()
        self.js_files = set()
        self.json_files = set()
        self.pdf_files = set()
        self.db_files = set()
        self.other_important_files = set()
        
        # Crawler state
        self.is_crawling = False
        self.crawl_start_time = 0
        self.crawled_count = 0
        
        # Thread safety
        self.lock = threading.Lock()
        
        # User agents
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0"
        ]
        
        # Base domain info
        self.base_domain_info = tldextract.extract(self.base_url.get())
        
        # Setup logging to GUI
        self.log_queue = queue.Queue()
        self.setup_logging()
        
        # Setup UI
        self.setup_ui()
        
        # Start log consumer
        self.consume_logs()

    def setup_logging(self):
        """Setup logging to both file and GUI"""
        # Remove any existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        # Create a custom handler for GUI
        class QueueHandler(logging.Handler):
            def __init__(self, log_queue):
                super().__init__()
                self.log_queue = log_queue

            def emit(self, record):
                self.log_queue.put(self.format(record))
                
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("crawler.log"),
                QueueHandler(self.log_queue)
            ]
        )

    def consume_logs(self):
        """Consume logs from queue and display in GUI"""
        try:
            while True:
                record = self.log_queue.get_nowait()
                self.log_area.configure(state='normal')
                self.log_area.insert(tk.END, record + "\n")
                self.log_area.configure(state='disabled')
                self.log_area.see(tk.END)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.consume_logs)

    def setup_ui(self):
        """Setup the user interface"""
        # Create main frames
        control_frame = ttk.LabelFrame(self.root, text="Crawler Controls", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        results_frame = ttk.LabelFrame(self.root, text="Results Location", padding=10)
        results_frame.pack(fill=tk.X, padx=10, pady=5)
        
        stats_frame = ttk.LabelFrame(self.root, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        log_frame = ttk.LabelFrame(self.root, text="Logs", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Control frame content
        ttk.Label(control_frame, text="Base URL:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(control_frame, textvariable=self.base_url, width=50).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(control_frame, text="Max Depth:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Spinbox(control_frame, textvariable=self.max_depth, from_=1, to=10, width=10).grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Label(control_frame, text="Delay (s):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Spinbox(control_frame, textvariable=self.delay, from_=0.1, to=10.0, increment=0.1, width=10).grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(control_frame, text="Timeout (s):").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Spinbox(control_frame, textvariable=self.timeout, from_=5, to=60, width=10).grid(row=1, column=3, padx=5, pady=2)
        
        ttk.Label(control_frame, text="Max Threads:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Spinbox(control_frame, textvariable=self.max_threads, from_=1, to=20, width=10).grid(row=2, column=1, padx=5, pady=2)
        
        self.start_button = ttk.Button(control_frame, text="Start Crawling", command=self.start_crawling)
        self.start_button.grid(row=2, column=2, padx=5, pady=5)
        
        self.stop_button = ttk.Button(control_frame, text="Stop Crawling", command=self.stop_crawling, state=tk.DISABLED)
        self.stop_button.grid(row=2, column=3, padx=5, pady=5)
        
        # Results location frame
        ttk.Label(results_frame, text="Results will be saved to:").pack(anchor=tk.W, pady=2)
        
        results_path_frame = ttk.Frame(results_frame)
        results_path_frame.pack(fill=tk.X, pady=5)
        
        self.results_entry = ttk.Entry(results_path_frame, textvariable=self.results_dir, width=80)
        self.results_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(results_path_frame, text="Browse", command=self.browse_results_dir).pack(side=tk.RIGHT)
        
        ttk.Label(results_frame, text="Files to be created: all_urls.txt, subdomains.txt, js_files.txt, json_files.txt, pdf_files.txt, db_files.txt, hidden_paths.txt, important_files.txt, external_links.txt, broken_links.txt, crawl_report.csv").pack(anchor=tk.W, pady=2)
        
        # Stats frame content
        stats_subframe = ttk.Frame(stats_frame)
        stats_subframe.pack(fill=tk.BOTH, expand=True)
        
        # Stats labels
        self.total_links_var = tk.StringVar(value="Total URLs: 0")
        self.subdomain_links_var = tk.StringVar(value="Subdomains: 0")
        self.js_files_var = tk.StringVar(value="JS Files: 0")
        self.json_files_var = tk.StringVar(value="JSON Files: 0")
        self.pdf_files_var = tk.StringVar(value="PDF Files: 0")
        self.db_files_var = tk.StringVar(value="DB Files: 0")
        self.hidden_paths_var = tk.StringVar(value="Hidden Paths: 0")
        self.external_links_var = tk.StringVar(value="External Links: 0")
        self.broken_links_var = tk.StringVar(value="Broken Links: 0")
        self.visited_urls_var = tk.StringVar(value="Visited URLs: 0")
        self.elapsed_time_var = tk.StringVar(value="Elapsed Time: 0s")
        
        ttk.Label(stats_subframe, textvariable=self.total_links_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.subdomain_links_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.js_files_var).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.json_files_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.pdf_files_var).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.db_files_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.hidden_paths_var).grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.external_links_var).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.broken_links_var).grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.visited_urls_var).grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.elapsed_time_var).grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
        
        # Progress bar
        self.progress = ttk.Progressbar(stats_subframe, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=10)
        
        # Configure grid weights
        stats_subframe.columnconfigure(0, weight=1)
        stats_subframe.columnconfigure(1, weight=1)
        stats_subframe.rowconfigure(6, weight=1)
        
        # Log frame content
        self.log_area = scrolledtext.ScrolledText(log_frame, height=15, state='disabled')
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        # Export buttons
        export_frame = ttk.Frame(log_frame)
        export_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(export_frame, text="Export All Data", command=self.export_all_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Generate Report", command=self.generate_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Open Results Folder", command=self.open_results_folder).pack(side=tk.LEFT, padx=5)

    def browse_results_dir(self):
        """Browse for a results directory"""
        directory = filedialog.askdirectory(initialdir=self.results_dir.get())
        if directory:
            self.results_dir.set(directory)

    def open_results_folder(self):
        """Open the results folder in file explorer"""
        try:
            if not os.path.exists(self.results_dir.get()):
                messagebox.showinfo("Info", "Results folder doesn't exist yet. Run the crawler first.")
                return
                
            if sys.platform == "win32":
                os.startfile(self.results_dir.get())
            elif sys.platform == "darwin":
                os.system(f"open '{self.results_dir.get()}'")
            else:
                os.system(f"xdg-open '{self.results_dir.get()}'")
        except Exception as e:
            logging.error(f"Error opening results folder: {e}")
            messagebox.showerror("Error", f"Could not open results folder: {e}")

    def update_stats(self):
        """Update the statistics display"""
        self.total_links_var.set(f"Total URLs: {len(self.all_links)}")
        self.subdomain_links_var.set(f"Subdomains: {len(self.subdomain_links)}")
        self.js_files_var.set(f"JS Files: {len(self.js_files)}")
        self.json_files_var.set(f"JSON Files: {len(self.json_files)}")
        self.pdf_files_var.set(f"PDF Files: {len(self.pdf_files)}")
        self.db_files_var.set(f"DB Files: {len(self.db_files)}")
        self.hidden_paths_var.set(f"Hidden Paths: {len(self.hidden_paths)}")
        self.external_links_var.set(f"External Links: {len(self.external_links)}")
        self.broken_links_var.set(f"Broken Links: {len(self.broken_links)}")
        self.visited_urls_var.set(f"Visited URLs: {len(self.visited)}")
        
        if self.is_crawling:
            elapsed = time.time() - self.crawl_start_time
            self.elapsed_time_var.set(f"Elapsed Time: {elapsed:.1f}s")
            self.root.after(1000, self.update_stats)

    def normalize_url(self, url):
        """Normalize URL"""
        try:
            parsed = urlparse(url)
            normalized = parsed._replace(fragment="", scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower())
            path = normalized.path.rstrip('/') or '/'
            normalized = normalized._replace(path=path)
            return urlunparse(normalized)
        except Exception:
            return url

    def can_fetch_url(self, url):
        """Robots.txt check"""
        try:
            rp = RobotFileParser()
            rp.set_url(urljoin(self.base_url.get(), "/robots.txt"))
            rp.read()
            return rp.can_fetch("*", url)
        except:
            return True

    def is_subdomain(self, url):
        """Check if URL is a subdomain"""
        try:
            domain_info = tldextract.extract(url)
            return (domain_info.domain == self.base_domain_info.domain and 
                    domain_info.suffix == self.base_domain_info.suffix and
                    domain_info.subdomain and 
                    domain_info.subdomain != self.base_domain_info.subdomain)
        except:
            return False

    def is_same_domain(self, url):
        """Check if URL is from the same domain"""
        try:
            domain_info = tldextract.extract(url)
            return (domain_info.domain == self.base_domain_info.domain and 
                    domain_info.suffix == self.base_domain_info.suffix)
        except:
            return False

    def is_external(self, url):
        """Check if URL is external"""
        try:
            domain_info = tldextract.extract(url)
            return (domain_info.domain != self.base_domain_info.domain or 
                    domain_info.suffix != self.base_domain_info.suffix)
        except:
            return True

    def is_hidden_path(self, url):
        """Check if URL contains hidden paths (starting with dot)"""
        parsed = urlparse(url)
        path_segments = parsed.path.split('/')
        return any(segment.startswith('.') for segment in path_segments if segment)

    def categorize_file(self, url):
        """Categorize file based on extension"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        if path.endswith('.js'):
            self.js_files.add(url)
        elif path.endswith('.json'):
            self.json_files.add(url)
        elif path.endswith('.pdf'):
            self.pdf_files.add(url)
        elif any(path.endswith(ext) for ext in ['.sql', '.db', '.sqlite', '.mdb', '.dbf']):
            self.db_files.add(url)
        elif any(path.endswith(ext) for ext in ['.xml', '.yml', '.yaml', '.config', '.conf', '.ini', '.env']):
            self.other_important_files.add(url)
        elif self.is_hidden_path(url):
            self.hidden_paths.add(url)

    def init_driver(self):
        """Initialize Chrome driver with multiple fallback options"""
        try:
            options = Options()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'--user-agent={random.choice(self.user_agents)}')
            options.add_argument('--headless')
            
            # Try multiple approaches to initialize the driver
            try:
                # First try: Use WebDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except Exception as e:
                logging.warning(f"WebDriverManager failed: {e}. Trying alternative methods...")
                
                # Second try: Use system chromedriver
                try:
                    # Check if chromedriver is already installed
                    chromedriver_path = None
                    possible_paths = [
                        '/usr/bin/chromedriver',
                        '/usr/local/bin/chromedriver',
                        '/snap/bin/chromium.chromedriver'
                    ]
                    
                    for path in possible_paths:
                        if os.path.exists(path):
                            chromedriver_path = path
                            break
                    
                    if chromedriver_path:
                        service = Service(chromedriver_path)
                        driver = webdriver.Chrome(service=service, options=options)
                    else:
                        # Third try: Use chromium instead of chrome
                        options.binary_location = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else None
                        driver = webdriver.Chrome(options=options)
                except Exception as e2:
                    logging.warning(f"System chromedriver failed: {e2}. Trying direct connection...")
                    
                    # Fourth try: Use remote webdriver (if available)
                    try:
                        from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
                        driver = RemoteWebDriver(command_executor='http://localhost:9515', options=options)
                    except:
                        # Final try: Use requests instead of selenium for basic crawling
                        logging.error("All Chrome driver initialization methods failed. Using requests-based fallback.")
                        return None
            
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": random.choice(self.user_agents)})
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        except Exception as e:
            logging.error(f"Failed to initialize driver: {e}")
            return None

    def extract_links_requests(self, url):
        """Extract links using requests as a fallback when selenium fails"""
        links = set()
        if not self.can_fetch_url(url):
            logging.info(f"Skipping {url} due to robots.txt")
            return links
            
        try:
            headers = {'User-Agent': random.choice(self.user_agents)}
            response = requests.get(url, headers=headers, timeout=self.timeout.get(), verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract all links
            for a_tag in soup.find_all("a", href=True):
                href = a_tag['href'].strip()
                if not href or href.startswith(('javascript:', 'mailto:', 'tel:')):
                    continue
                full_url = urljoin(url, href)
                normalized_url = self.normalize_url(full_url)
                links.add(normalized_url)
                
                with self.lock:
                    self.all_links.add(normalized_url)
                    
                    # Categorize the URL
                    if self.is_external(normalized_url):
                        self.external_links.add(normalized_url)
                    elif self.is_subdomain(normalized_url):
                        self.subdomain_links.add(normalized_url)
                    
                    # Categorize files
                    self.categorize_file(normalized_url)
            
            # Also extract links from other tags that might contain URLs
            for tag in soup.find_all(["link", "script", "img", "iframe"], src=True):
                src = tag['src'].strip()
                if not src:
                    continue
                full_url = urljoin(url, src)
                normalized_url = self.normalize_url(full_url)
                links.add(normalized_url)
                
                with self.lock:
                    self.all_links.add(normalized_url)
                    self.categorize_file(normalized_url)
            
            logging.info(f"Extracted {len(links)} links from {url} using requests")
        except Exception as e:
            logging.error(f"Error extracting from {url} using requests: {e}")
            with self.lock:
                self.broken_links.add(url)
        return links

    def crawl_worker(self, url, depth):
        """Worker function for crawling"""
        driver = self.init_driver()
        
        # If driver initialization failed, use requests fallback
        if not driver:
            logging.info(f"Using requests fallback for {url}")
            try:
                if depth > self.max_depth.get() or self.normalize_url(url) in self.visited:
                    return []
                    
                with self.lock:
                    self.visited.add(self.normalize_url(url))
                    self.crawled_count += 1
                    
                logging.info(f"Crawling {url} at depth {depth} using requests")
                links = self.extract_links_requests(url)
                return [(link, depth+1) for link in links if self.is_same_domain(link) or self.is_subdomain(link)]
            except Exception as e:
                logging.error(f"Error crawling {url} with requests: {e}")
                with self.lock:
                    self.broken_links.add(url)
                return []
        else:
            # Use selenium as normal
            results = []
            try:
                if depth > self.max_depth.get() or self.normalize_url(url) in self.visited:
                    return []
                    
                with self.lock:
                    self.visited.add(self.normalize_url(url))
                    self.crawled_count += 1
                    
                logging.info(f"Crawling {url} at depth {depth}")
                links = self.extract_links_selenium(url, driver)
                results.extend([(link, depth+1) for link in links if self.is_same_domain(link) or self.is_subdomain(link)])
            except Exception as e:
                logging.error(f"Error crawling {url}: {e}")
                with self.lock:
                    self.broken_links.add(url)
            finally:
                driver.quit()
            return results

    def extract_links_selenium(self, url, driver):
        """Extract links using Selenium"""
        links = set()
        if not self.can_fetch_url(url):
            logging.info(f"Skipping {url} due to robots.txt")
            return links
            
        try:
            driver.get(url)
            WebDriverWait(driver, self.timeout.get()).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Scroll to load lazy content
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract all links
            for a_tag in soup.find_all("a", href=True):
                href = a_tag['href'].strip()
                if not href or href.startswith(('javascript:', 'mailto:', 'tel:')):
                    continue
                full_url = urljoin(url, href)
                normalized_url = self.normalize_url(full_url)
                links.add(normalized_url)
                
                with self.lock:
                    self.all_links.add(normalized_url)
                    
                    # Categorize the URL
                    if self.is_external(normalized_url):
                        self.external_links.add(normalized_url)
                    elif self.is_subdomain(normalized_url):
                        self.subdomain_links.add(normalized_url)
                    
                    # Categorize files
                    self.categorize_file(normalized_url)
            
            # Also extract links from other tags that might contain URLs
            for tag in soup.find_all(["link", "script", "img", "iframe"], src=True):
                src = tag['src'].strip()
                if not src:
                    continue
                full_url = urljoin(url, src)
                normalized_url = self.normalize_url(full_url)
                links.add(normalized_url)
                
                with self.lock:
                    self.all_links.add(normalized_url)
                    self.categorize_file(normalized_url)
            
            logging.info(f"Extracted {len(links)} links from {url}")
        except Exception as e:
            logging.error(f"Error extracting from {url}: {e}")
            with self.lock:
                self.broken_links.add(url)
        return links

    def crawl_with_threads(self):
        """Main crawling function with threads"""
        logging.info("[*] Starting multi-threaded crawling...")
        start_url = self.base_url.get()
        self.base_domain_info = tldextract.extract(start_url)
        
        queue = deque([(start_url, 0)])
        
        with ThreadPoolExecutor(max_workers=self.max_threads.get()) as executor:
            futures = {}
            while queue or futures:
                # Submit new tasks
                while queue and self.is_crawling:
                    url, depth = queue.popleft()
                    if depth <= self.max_depth.get() and self.normalize_url(url) not in self.visited:
                        future = executor.submit(self.crawl_worker, url, depth)
                        futures[future] = (url, depth)
                
                # Process completed tasks
                for future in list(futures):
                    if future.done():
                        try:
                            new_links = future.result()
                            for link, new_depth in new_links:
                                if self.normalize_url(link) not in self.visited and new_depth <= self.max_depth.get():
                                    queue.append((link, new_depth))
                        except Exception as e:
                            logging.error(f"Error in thread: {e}")
                        finally:
                            del futures[future]
                
                # If no more work and all futures are done, break
                if not queue and not futures:
                    break
                    
                # Delay between processing
                time.sleep(self.delay.get() * random.uniform(0.5, 1.5))
                
                # Check if we should stop crawling
                if not self.is_crawling:
                    break
                
        logging.info("[*] Multi-threaded crawling finished!")
        self.crawling_finished()

    def start_crawling(self):
        """Start the crawling process"""
        if not self.base_url.get():
            messagebox.showerror("Error", "Please enter a valid base URL")
            return
            
        # Create results directory if it doesn't exist
        if not os.path.exists(self.results_dir.get()):
            try:
                os.makedirs(self.results_dir.get())
                logging.info(f"Created results directory: {self.results_dir.get()}")
            except Exception as e:
                logging.error(f"Error creating results directory: {e}")
                messagebox.showerror("Error", f"Could not create results directory: {e}")
                return
            
        self.is_crawling = True
        self.crawl_start_time = time.time()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.start(10)
        
        # Reset data structures
        self.visited.clear()
        self.all_links.clear()
        self.subdomain_links.clear()
        self.external_links.clear()
        self.broken_links.clear()
        self.hidden_paths.clear()
        self.js_files.clear()
        self.json_files.clear()
        self.pdf_files.clear()
        self.db_files.clear()
        self.other_important_files.clear()
        self.crawled_count = 0
        
        # Start crawling in a separate thread
        self.crawl_thread = Thread(target=self.crawl_with_threads, daemon=True)
        self.crawl_thread.start()
        
        # Start updating stats
        self.update_stats()

    def stop_crawling(self):
        """Stop the crawling process"""
        self.is_crawling = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress.stop()
        logging.info("Crawling stopped by user")
        # Save results when stopped
        self.save_results()

    def crawling_finished(self):
        """Called when crawling finishes"""
        self.is_crawling = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress.stop()
        
        elapsed = time.time() - self.crawl_start_time
        logging.info(f"Crawling completed in {elapsed:.2f} seconds")
        self.save_results()
        
        # Show completion message
        messagebox.showinfo("Completed", f"Crawling completed!\n\n"
                            f"Results saved to: {self.results_dir.get()}\n\n"
                            f"Visited: {len(self.visited)} URLs\n"
                            f"Found: {len(self.all_links)} links\n"
                            f"Time: {elapsed:.2f} seconds")

    def save_results(self):
        """Save results to files"""
        try:
            # Ensure directory exists
            if not os.path.exists(self.results_dir.get()):
                os.makedirs(self.results_dir.get())
            
            # Save all files to the specified directory
            with open(os.path.join(self.results_dir.get(), "all_urls.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.all_links)))
                
            with open(os.path.join(self.results_dir.get(), "subdomains.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.subdomain_links)))
                
            with open(os.path.join(self.results_dir.get(), "js_files.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.js_files)))
                
            with open(os.path.join(self.results_dir.get(), "json_files.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.json_files)))
                
            with open(os.path.join(self.results_dir.get(), "pdf_files.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.pdf_files)))
                
            with open(os.path.join(self.results_dir.get(), "db_files.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.db_files)))
                
            with open(os.path.join(self.results_dir.get(), "hidden_paths.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.hidden_paths)))
                
            with open(os.path.join(self.results_dir.get(), "important_files.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.other_important_files)))
                
            with open(os.path.join(self.results_dir.get(), "external_links.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.external_links)))
                
            with open(os.path.join(self.results_dir.get(), "broken_links.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.broken_links)))
            
            # Save CSV report
            with open(os.path.join(self.results_dir.get(), "crawl_report.csv"), "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Metric", "Count"])
                writer.writerow(["Total URLs", len(self.all_links)])
                writer.writerow(["Subdomains", len(self.subdomain_links)])
                writer.writerow(["JS Files", len(self.js_files)])
                writer.writerow(["JSON Files", len(self.json_files)])
                writer.writerow(["PDF Files", len(self.pdf_files)])
                writer.writerow(["Database Files", len(self.db_files)])
                writer.writerow(["Hidden Paths", len(self.hidden_paths)])
                writer.writerow(["Important Files", len(self.other_important_files)])
                writer.writerow(["External Links", len(self.external_links)])
                writer.writerow(["Broken Links", len(self.broken_links)])
                writer.writerow(["Visited URLs", len(self.visited)])
            
            # Save JSON data
            with open(os.path.join(self.results_dir.get(), "crawl_data.json"), "w", encoding="utf-8") as f:
                json.dump({
                    "all_urls": list(self.all_links),
                    "subdomains": list(self.subdomain_links),
                    "js_files": list(self.js_files),
                    "json_files": list(self.json_files),
                    "pdf_files": list(self.pdf_files),
                    "db_files": list(self.db_files),
                    "hidden_paths": list(self.hidden_paths),
                    "important_files": list(self.other_important_files),
                    "external_links": list(self.external_links),
                    "broken_links": list(self.broken_links),
                    "visited": list(self.visited)
                }, f, indent=4)
                
            logging.info(f"Results saved to: {self.results_dir.get()}")
        except Exception as e:
            logging.error(f"Error saving results: {e}")

    def export_all_data(self):
        """Export all data to a zip file"""
        self.save_results()
        messagebox.showinfo("Export", f"All data has been exported to:\n{self.results_dir.get()}")

    def generate_report(self):
        """Generate a detailed report"""
        try:
            report_path = os.path.join(self.results_dir.get(), "crawl_detailed_report.txt")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("Advanced Web Crawler Detailed Report\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Base URL: {self.base_url.get()}\n")
                f.write(f"Max Depth: {self.max_depth.get()}\n")
                f.write(f"Max Threads: {self.max_threads.get()}\n")
                f.write(f"Delay: {self.delay.get()} seconds\n")
                f.write(f"Results Location: {self.results_dir.get()}\n\n")
                
                f.write("Summary:\n")
                f.write(f"  Total URLs: {len(self.all_links)}\n")
                f.write(f"  Subdomains: {len(self.subdomain_links)}\n")
                f.write(f"  JS Files: {len(self.js_files)}\n")
                f.write(f"  JSON Files: {len(self.json_files)}\n")
                f.write(f"  PDF Files: {len(self.pdf_files)}\n")
                f.write(f"  Database Files: {len(self.db_files)}\n")
                f.write(f"  Hidden Paths: {len(self.hidden_paths)}\n")
                f.write(f"  Important Files: {len(self.other_important_files)}\n")
                f.write(f"  External Links: {len(self.external_links)}\n")
                f.write(f"  Broken Links: {len(self.broken_links)}\n")
                f.write(f"  Visited URLs: {len(self.visited)}\n\n")
                
                f.write("Top 10 Most Common Paths:\n")
                from collections import Counter
                paths = Counter(urlparse(url).path for url in self.all_links)
                for path, count in paths.most_common(10):
                    f.write(f"  {path}: {count}\n")
                    
            logging.info(f"Detailed report generated: {report_path}")
            messagebox.showinfo("Report Generated", f"Detailed report saved to:\n{report_path}")
        except Exception as e:
            logging.error(f"Error generating report: {e}")
            messagebox.showerror("Error", f"Failed to generate report: {e}")

def main():
    """Main function"""
    root = tk.Tk()
    app = AdvancedWebCrawler(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (root.quit(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()
