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
from tkinter import ttk, scrolledtext, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from threading import Thread
import queue
import sys

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class eBayWebCrawler:
    def __init__(self, root):
        self.root = root
        self.root.title("eBay Web Crawler")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # Configuration with defaults
        self.base_url = tk.StringVar(value="https://www.ebay.com")
        self.max_depth = tk.IntVar(value=2)
        self.delay = tk.DoubleVar(value=2.0)
        self.timeout = tk.IntVar(value=15)
        self.max_threads = tk.IntVar(value=5)
        
        # Data structures
        self.visited = set()
        self.all_links = set()
        self.subdomain_links = set()
        self.specific_files = set()
        self.external_links = set()
        self.broken_links = set()
        self.link_data = {}
        
        # Crawler state
        self.is_crawling = False
        self.crawl_start_time = 0
        self.crawled_count = 0
        
        # Thread safety
        self.lock = threading.Lock()
        self.task_queue = queue.Queue()
        
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
        
        # Stats frame content
        stats_subframe = ttk.Frame(stats_frame)
        stats_subframe.pack(fill=tk.BOTH, expand=True)
        
        # Stats labels
        self.total_links_var = tk.StringVar(value="Total Links: 0")
        self.subdomain_links_var = tk.StringVar(value="Subdomain Links: 0")
        self.specific_files_var = tk.StringVar(value="Specific Files: 0")
        self.external_links_var = tk.StringVar(value="External Links: 0")
        self.broken_links_var = tk.StringVar(value="Broken Links: 0")
        self.visited_urls_var = tk.StringVar(value="Visited URLs: 0")
        self.elapsed_time_var = tk.StringVar(value="Elapsed Time: 0s")
        
        ttk.Label(stats_subframe, textvariable=self.total_links_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.subdomain_links_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.specific_files_var).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.external_links_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.broken_links_var).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.visited_urls_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(stats_subframe, textvariable=self.elapsed_time_var).grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        
        # Progress bar
        self.progress = ttk.Progressbar(stats_subframe, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=10)
        
        # Visualization frame
        viz_frame = ttk.Frame(stats_subframe)
        viz_frame.grid(row=0, column=2, rowspan=5, padx=10, pady=5, sticky=tk.NSEW)
        
        # Create a simple visualization
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=viz_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        stats_subframe.columnconfigure(0, weight=1)
        stats_subframe.columnconfigure(1, weight=1)
        stats_subframe.columnconfigure(2, weight=2)
        stats_subframe.rowconfigure(4, weight=1)
        
        # Log frame content
        self.log_area = scrolledtext.ScrolledText(log_frame, height=15, state='disabled')
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        # Export buttons
        export_frame = ttk.Frame(log_frame)
        export_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(export_frame, text="Export All Data", command=self.export_all_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Generate Report", command=self.generate_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Update Visualization", command=self.update_visualization).pack(side=tk.LEFT, padx=5)

    def update_visualization(self):
        """Update the statistics visualization"""
        self.ax.clear()
        
        categories = ['Total', 'Subdomains', 'Files', 'External', 'Broken', 'Visited']
        values = [
            len(self.all_links), 
            len(self.subdomain_links), 
            len(self.specific_files), 
            len(self.external_links), 
            len(self.broken_links), 
            len(self.visited)
        ]
        
        colors = ['blue', 'green', 'orange', 'red', 'purple', 'cyan']
        bars = self.ax.bar(categories, values, color=colors)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            self.ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{value}', ha='center', va='bottom')
        
        self.ax.set_title('Crawling Statistics')
        self.ax.set_ylabel('Count')
        self.fig.tight_layout()
        self.canvas.draw()

    def update_stats(self):
        """Update the statistics display"""
        self.total_links_var.set(f"Total Links: {len(self.all_links)}")
        self.subdomain_links_var.set(f"Subdomain Links: {len(self.subdomain_links)}")
        self.specific_files_var.set(f"Specific Files: {len(self.specific_files)}")
        self.external_links_var.set(f"External Links: {len(self.external_links)}")
        self.broken_links_var.set(f"Broken Links: {len(self.broken_links)}")
        self.visited_urls_var.set(f"Visited URLs: {len(self.visited)}")
        
        if self.is_crawling:
            elapsed = time.time() - self.crawl_start_time
            self.elapsed_time_var.set(f"Elapsed Time: {elapsed:.1f}s")
            self.root.after(1000, self.update_stats)
        
        self.update_visualization()

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

    def init_driver(self):
        """Initialize Chrome driver"""
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
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": random.choice(self.user_agents)})
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        except Exception as e:
            logging.error(f"Failed to initialize driver: {e}")
            return None

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
            for a_tag in soup.find_all("a", href=True):
                href = a_tag['href'].strip()
                if not href or href.startswith(('javascript:', 'mailto:', 'tel:')):
                    continue
                full_url = urljoin(url, href)
                normalized_url = self.normalize_url(full_url)
                links.add(normalized_url)
                
                with self.lock:
                    self.all_links.add(normalized_url)
                    if self.is_external(normalized_url):
                        self.external_links.add(normalized_url)
                    elif self.is_subdomain(normalized_url):
                        self.subdomain_links.add(normalized_url)
                    if re.search(r'\.(php|html|aspx|jsp|cfm)(\?|$|/)', normalized_url, re.IGNORECASE):
                        self.specific_files.add(normalized_url)
            
            logging.info(f"Extracted {len(links)} links from {url}")
        except Exception as e:
            logging.error(f"Selenium error extracting from {url}: {e}")
            with self.lock:
                self.broken_links.add(url)
        return links

    def crawl_worker(self, url, depth):
        """Worker function for crawling"""
        driver = self.init_driver()
        if not driver:
            logging.error("Failed to initialize driver in thread")
            return []
            
        results = []
        try:
            if depth > self.max_depth.get() or self.normalize_url(url) in self.visited:
                return []
                
            with self.lock:
                self.visited.add(self.normalize_url(url))
                self.crawled_count += 1
                
            logging.info(f"Crawling {url} at depth {depth}")
            links = self.extract_links_selenium(url, driver)
            results.extend([(link, depth+1) for link in links if self.is_same_domain(link)])
        finally:
            driver.quit()
        return results

    def crawl_with_threads(self):
        """Main crawling function with threads"""
        logging.info("[*] Starting multi-threaded crawling...")
        start_url = self.base_url.get()
        self.base_domain_info = tldextract.extract(start_url)
        
        queue = deque([(start_url, 0)])
        
        with ThreadPoolExecutor(max_workers=self.max_threads.get()) as executor:
            futures = {}
            while (queue or futures) and self.is_crawling:
                # Submit new tasks
                while queue and self.is_crawling:
                    url, depth = queue.popleft()
                    future = executor.submit(self.crawl_worker, url, depth)
                    futures[future] = depth
                
                # Process completed tasks
                for future in list(futures):
                    if future.done():
                        try:
                            new_links = future.result()
                            for link, new_depth in new_links:
                                if self.normalize_url(link) not in self.visited:
                                    queue.append((link, new_depth))
                        except Exception as e:
                            logging.error(f"Error in thread: {e}")
                        finally:
                            futures.pop(future)
                
                # Delay between processing
                time.sleep(self.delay.get() * random.uniform(0.5, 1.5))
                
        logging.info("[*] Multi-threaded crawling finished!")
        self.crawling_finished()

    def start_crawling(self):
        """Start the crawling process"""
        if not self.base_url.get():
            messagebox.showerror("Error", "Please enter a valid base URL")
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
        self.specific_files.clear()
        self.external_links.clear()
        self.broken_links.clear()
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
                            f"Visited: {len(self.visited)} URLs\n"
                            f"Found: {len(self.all_links)} links\n"
                            f"Time: {elapsed:.2f} seconds")

    def save_results(self):
        """Save results to files"""
        try:
            with open("all_links.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.all_links)))
            with open("subdomain_links.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.subdomain_links)))
            with open("specific_files.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.specific_files)))
            with open("external_links.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.external_links)))
            with open("broken_links.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(self.broken_links)))
            
            with open("crawl_report.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Metric", "Count"])
                writer.writerow(["Total Links", len(self.all_links)])
                writer.writerow(["Subdomain Links", len(self.subdomain_links)])
                writer.writerow(["Specific Files", len(self.specific_files)])
                writer.writerow(["External Links", len(self.external_links)])
                writer.writerow(["Broken Links", len(self.broken_links)])
                writer.writerow(["Visited URLs", len(self.visited)])
            
            with open("crawl_data.json", "w", encoding="utf-8") as f:
                json.dump({
                    "all_links": list(self.all_links),
                    "subdomain_links": list(self.subdomain_links),
                    "specific_files": list(self.specific_files),
                    "external_links": list(self.external_links),
                    "broken_links": list(self.broken_links),
                    "visited": list(self.visited)
                }, f, indent=4)
                
            logging.info("Results saved to files")
        except Exception as e:
            logging.error(f"Error saving results: {e}")

    def export_all_data(self):
        """Export all data to a zip file"""
        self.save_results()
        messagebox.showinfo("Export", "All data has been exported to files")

    def generate_report(self):
        """Generate a detailed report"""
        try:
            report_path = "crawl_detailed_report.txt"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("eBay Web Crawler Detailed Report\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Base URL: {self.base_url.get()}\n")
                f.write(f"Max Depth: {self.max_depth.get()}\n")
                f.write(f"Max Threads: {self.max_threads.get()}\n")
                f.write(f"Delay: {self.delay.get()} seconds\n\n")
                
                f.write("Summary:\n")
                f.write(f"  Total Links: {len(self.all_links)}\n")
                f.write(f"  Subdomain Links: {len(self.subdomain_links)}\n")
                f.write(f"  Specific Files: {len(self.specific_files)}\n")
                f.write(f"  External Links: {len(self.external_links)}\n")
                f.write(f"  Broken Links: {len(self.broken_links)}\n")
                f.write(f"  Visited URLs: {len(self.visited)}\n\n")
                
                f.write("Top 10 Most Common Paths:\n")
                from collections import Counter
                paths = Counter(urlparse(url).path for url in self.all_links)
                for path, count in paths.most_common(10):
                    f.write(f"  {path}: {count}\n")
                    
            logging.info(f"Detailed report generated: {report_path}")
            messagebox.showinfo("Report Generated", f"Detailed report saved to {report_path}")
        except Exception as e:
            logging.error(f"Error generating report: {e}")
            messagebox.showerror("Error", f"Failed to generate report: {e}")

def main():
    """Main function"""
    root = tk.Tk()
    app = eBayWebCrawler(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (root.quit(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()