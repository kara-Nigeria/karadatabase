"""
Progress visualization utilities
"""

import sys
import time
from typing import Optional, Dict, Any
from datetime import datetime

from tqdm import tqdm
from colorama import init, Fore, Style

# Initialize colorama
init()

class ProgressBar:
    """A wrapper around tqdm to provide a consistent progress bar"""
    
    def __init__(self, total: int, desc: str, unit: str = "items"):
        self.progress_bar = tqdm(
            total=total,
            desc=f"{Fore.BLUE}{desc}{Style.RESET_ALL}",
            unit=unit,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
        )
    
    def update(self, n: int = 1):
        """Update the progress bar"""
        self.progress_bar.update(n)
    
    def set_description(self, desc: str):
        """Set the description of the progress bar"""
        self.progress_bar.set_description(f"{Fore.BLUE}{desc}{Style.RESET_ALL}")
    
    def close(self):
        """Close the progress bar"""
        self.progress_bar.close()

class MigrationStatus:
    """A class to track and display migration status"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.entity_progress = {}
    
    def update_entity_progress(self, entity_type: str, progress: Dict):
        """Update the progress for an entity type"""
        self.entity_progress[entity_type] = progress
    
    def get_elapsed_time(self) -> str:
        """Get the elapsed time since the start of the migration"""
        elapsed = datetime.now() - self.start_time
        hours, remainder = divmod(elapsed.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    def print_summary(self):
        """Print a summary of the migration status"""
        elapsed_time = self.get_elapsed_time()
        
        print("\n" + "="*80)
        print(f"{Fore.CYAN}MIGRATION SUMMARY{Style.RESET_ALL}")
        print(f"Elapsed time: {Fore.YELLOW}{elapsed_time}{Style.RESET_ALL}")
        print("-"*80)
        
        for entity_type, progress in self.entity_progress.items():
            status = progress.get('status', 'unknown')
            total = progress.get('total_count', 0)
            processed = progress.get('processed_count', 0)
            success = progress.get('success_count', 0)
            errors = progress.get('error_count', 0)
            
            # Calculate percentage
            percentage = 0
            if total > 0:
                percentage = (processed / total) * 100
            
            # Determine color based on status
            color = Fore.WHITE
            if status == 'completed':
                color = Fore.GREEN
            elif status == 'in_progress':
                color = Fore.BLUE
            elif status == 'failed':
                color = Fore.RED
            elif status == 'pending':
                color = Fore.YELLOW
            
            print(f"{Fore.WHITE}Entity: {Fore.CYAN}{entity_type.capitalize()}{Style.RESET_ALL}")
            print(f"Status: {color}{status.upper()}{Style.RESET_ALL}")
            print(f"Progress: {processed}/{total} ({percentage:.1f}%)")
            print(f"Success: {Fore.GREEN}{success}{Style.RESET_ALL}")
            print(f"Errors: {Fore.RED}{errors}{Style.RESET_ALL}")
            print("-"*80)
        
        print("="*80 + "\n")

def print_banner():
    """Print a banner for the migration tool"""
    banner = f"""
    {Fore.CYAN}╔═══════════════════════════════════════════════════════════╗
    ║  {Fore.YELLOW}KARA TO MEDUSA.JS MIGRATION TOOL{Fore.CYAN}                      ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Migrating Products and Categories from Kara to Medusa.js  ║
    ╚═══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
    """
    print(banner)

def print_step(step: str, message: str):
    """Print a step in the migration process"""
    print(f"\n{Fore.BLUE}[STEP] {Fore.CYAN}{step}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{message}{Style.RESET_ALL}")
    print("-"*80)