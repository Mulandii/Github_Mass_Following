import requests
import json
import time
import random
import sys
from typing import Dict, Optional, Tuple, List
import logging
import re
from datetime import datetime
import os
import base64
from urllib.parse import urljoin
import hmac
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Color Codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'  
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    GRADIENT = [
        '\033[38;5;196m',
        '\033[38;5;202m',
        '\033[38;5;208m',
        '\033[38;5;214m',
        '\033[38;5;220m',
        '\033[38;5;226m',
        '\033[38;5;190m',
        '\033[38;5;154m',
        '\033[38;5;118m',
        '\033[38;5;46m',
    ]

class GitHubTool:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://github.com"
        self.api_url = "https://api.github.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'Accept': 'application/vnd.github.v3+json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        self.session.headers.update(self.headers)
        self.username = None
        self.access_token = None
        self.session_start_time = datetime.now()
        self.followed_users = []
        self.starred_repos = []

        # OPTIMIZATION: cache the logged-in user's following list so we
        # never fetch it twice in the same session (shared by both the
        # followback cleaner and the seed-follower extractor).
        self._cached_following: Optional[List[str]] = None
        
        self.github_features = {
            'follow': 'Follow users',
            'unfollow': 'Unfollow users',
            'star': 'Star repositories',
            'unstar': 'Unstar repositories',
            'watch': 'Watch repositories',
            'fork': 'Fork repositories',
            'issue': 'Create issues',
            'pull': 'Create pull requests'
        }
        
        self.report_categories = [
            "spam", "inappropriate", "hate_speech", "harassment",
            "violence", "copyright", "impersonation", "other"
        ]
        
        self.report_reasons = [
            "Spam or unwanted commercial content",
            "Inappropriate content or nudity",
            "Hate speech or discriminatory content",
            "Harassment or bullying",
            "Violence or harmful behavior",
            "Copyright infringement",
            "Impersonation or fake account",
            "Other violations"
        ]
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print('\033[H\033[J', end='')
    
    def print_banner(self):
        self.clear_screen()
        banner = [
            "   _____ _ _   _    _       _               ",
            "  / ____(_) | | |  | |     | |              ",
            " | |  __ _| |_| |__| |_   _| |__    ",
            " | | |_ | | __|  __  | | | | '_ \ ",
            " | |__| | | |_| |  | | |_| | |_) |   ",
            "  \_____|_|\__|_|  |_|\__,_|_.__/ ",
            "                                              ",
            "  ____        _                           ",
            " |  _ \      | |                       ",
            " | |_) | ___ | |_             ",
            " |  _ < / _ \| __           ",
            " | |_) | (_) | |_             ",
            " |____/ \___/ \__|               "
        ]
        print(f"{Colors.BRIGHT_CYAN}{'='*70}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}")
        for i, line in enumerate(banner):
            color = Colors.GRADIENT[i % len(Colors.GRADIENT)]
            print(f"{color}{line}{Colors.RESET}")
        print(f"{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'='*70}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}┌────────────────────────────────────────────────────────────┐{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.BRIGHT_CYAN}             GITHUB TOOL v3.6      {Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.BRIGHT_YELLOW}     Developed with  ❤️ by Illusivehacks         {Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.BRIGHT_CYAN}     NEW: Seed User Follower Extractor            {Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}└────────────────────────────────────────────────────────────┘{Colors.RESET}\n")
    
    def print_header(self, text: str, color: str = Colors.BRIGHT_CYAN):
        print(f"\n{color}{'═' * 60}{Colors.RESET}")
        print(f"{color}{Colors.BOLD}✨ {text} ✨{Colors.RESET}")
        print(f"{color}{'═' * 60}{Colors.RESET}\n")
    
    def print_success(self, text: str):
        print(f"{Colors.BRIGHT_GREEN}✅ {text}{Colors.RESET}")
    
    def print_error(self, text: str):
        print(f"{Colors.BRIGHT_RED}❌ {text}{Colors.RESET}")
    
    def print_warning(self, text: str):
        print(f"{Colors.BRIGHT_YELLOW}⚠️  {text}{Colors.RESET}")
    
    def print_info(self, text: str):
        print(f"{Colors.BRIGHT_BLUE}ℹ️  {text}{Colors.RESET}")
    
    def animate_loading(self, text: str, duration: int = 2):
        spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        end_time = time.time() + duration
        sys.stdout.write(f"{Colors.BRIGHT_BLUE}{text} ")
        sys.stdout.flush()
        while time.time() < end_time:
            for char in spinner:
                sys.stdout.write(f'\r{Colors.BRIGHT_BLUE}{text} {char}{Colors.RESET}')
                sys.stdout.flush()
                time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * (len(text) + 2) + '\r')
        sys.stdout.flush()

    # ──────────────────────────────────────────────────────────────────
    # OPTIMIZATION: shared rate-limit check — called every 5 pages only
    # instead of every single page (saves ~80% of rate-limit API calls).
    # ──────────────────────────────────────────────────────────────────
    def _check_rate_limit_low(self, threshold: int = 50) -> bool:
        """Return True (and warn) if core remaining < threshold."""
        try:
            r = self.session.get(f"{self.api_url}/rate_limit", timeout=5)
            if r.status_code == 200:
                remaining = r.json()['resources']['core']['remaining']
                if remaining < threshold:
                    self.print_warning(f"Low API rate limit: {remaining} requests remaining")
                    return True
        except Exception:
            pass
        return False

    # ──────────────────────────────────────────────────────────────────
    # OPTIMIZATION: verify multiple usernames in parallel
    # ──────────────────────────────────────────────────────────────────
    def verify_users_exist_bulk(self, usernames: List[str],
                                 max_workers: int = 10) -> Dict[str, bool]:
        """Verify multiple usernames concurrently. Returns {username: bool}"""
        results: Dict[str, bool] = {}

        def _check(uname):
            try:
                r = self.session.get(f"{self.api_url}/users/{uname}", timeout=5)
                return uname, r.status_code == 200
            except Exception:
                return uname, False

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for uname, exists in (f.result() for f in as_completed(
                    {ex.submit(_check, u): u for u in usernames})):
                results[uname] = exists

        return results

    def login_with_token(self, access_token: str) -> Tuple[bool, str]:
        try:
            self.print_header("GITHUB LOGIN")
            self.access_token = access_token
            self.session.headers.update({
                'Authorization': f'token {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            })
            self.animate_loading("Authenticating with GitHub API")
            response = self.session.get(f"{self.api_url}/user")
            
            if response.status_code == 200:
                user_data = response.json()
                self.username = user_data.get('login')
                self._cached_following = None   # reset cache on new login
                
                rate_response = self.session.get(f"{self.api_url}/rate_limit")
                if rate_response.status_code == 200:
                    rate_data = rate_response.json()
                    core_limit = rate_data['resources']['core']['limit']
                    remaining  = rate_data['resources']['core']['remaining']
                    self.print_success(f"Welcome, @{self.username}! ✨")
                    self.print_info(f"API Rate Limit: {remaining}/{core_limit} requests remaining")
                    if remaining < 100:
                        self.print_warning("Low API rate limit remaining!")
                    return True, f"Logged in as @{self.username}"
                else:
                    return True, f"Logged in as @{self.username} (rate limit check failed)"
            elif response.status_code == 401:
                return False, "Invalid access token ❌"
            elif response.status_code == 403:
                return False, "Rate limited or token permissions insufficient 🔐"
            else:
                return False, f"Login failed: HTTP {response.status_code}"
        except Exception as e:
            return False, f"Login error: {str(e)}"
    
    def login_with_credentials(self, username: str, password: str) -> Tuple[bool, str]:
        try:
            self.print_header("GITHUB LOGIN")
            self.animate_loading("Authenticating with GitHub")
            self.session.auth = (username, password)
            response = self.session.get(f"{self.api_url}/user")
            
            if response.status_code == 200:
                user_data = response.json()
                self.username = user_data.get('login')
                self._cached_following = None
                if 'X-GitHub-OTP' in response.headers:
                    return False, "Two-factor authentication required 🔐"
                self.print_success(f"Welcome, @{self.username}! ✨")
                return True, f"Logged in as @{self.username}"
            elif response.status_code == 401:
                if 'X-GitHub-OTP' in response.headers:
                    return False, "Two-factor authentication required 🔐"
                return False, "Invalid credentials ❌"
            elif response.status_code == 403:
                return False, "Rate limited or account locked 🔐"
            else:
                return False, f"Login failed: HTTP {response.status_code}"
        except Exception as e:
            return False, f"Login error: {str(e)}"
    
    def verify_user_exists(self, username: str) -> bool:
        try:
            response = self.session.get(f"{self.api_url}/users/{username}")
            return response.status_code == 200
        except:
            return False
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        try:
            self.animate_loading(f"Fetching info for @{username}")
            response = self.session.get(f"{self.api_url}/users/{username}")
            if response.status_code == 200:
                user_data = response.json()
                repos_response = self.session.get(user_data['repos_url'] + "?per_page=100")
                repos_data = repos_response.json() if repos_response.status_code == 200 else []
                total_stars = sum(repo.get('stargazers_count', 0) for repo in repos_data)
                total_forks = sum(repo.get('forks_count', 0) for repo in repos_data)
                languages = {}
                for repo in repos_data:
                    lang = repo.get('language')
                    if lang:
                        languages[lang] = languages.get(lang, 0) + 1
                top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
                return {
                    'username': user_data.get('login'),
                    'name': user_data.get('name'),
                    'bio': user_data.get('bio'),
                    'company': user_data.get('company'),
                    'location': user_data.get('location'),
                    'email': user_data.get('email'),
                    'blog': user_data.get('blog'),
                    'twitter': user_data.get('twitter_username'),
                    'followers': user_data.get('followers', 0),
                    'following': user_data.get('following', 0),
                    'public_repos': user_data.get('public_repos', 0),
                    'public_gists': user_data.get('public_gists', 0),
                    'hireable': user_data.get('hireable', False),
                    'created_at': user_data.get('created_at'),
                    'updated_at': user_data.get('updated_at'),
                    'avatar_url': user_data.get('avatar_url'),
                    'total_stars': total_stars,
                    'total_forks': total_forks,
                    'top_languages': top_languages,
                    'avg_repo_stars': total_stars / len(repos_data) if repos_data else 0
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    def follow_user(self, target_username: str) -> Tuple[bool, str]:
        try:
            if not self.username or not self.access_token:
                return False, "Please login with access token first!"
            if target_username == self.username:
                return False, "Cannot follow yourself! 🤔"
            self.animate_loading(f"Preparing to follow @{target_username}")
            time.sleep(random.uniform(1, 3))
            response = self.session.put(f"{self.api_url}/user/following/{target_username}")
            if response.status_code == 204:
                self.followed_users.append({
                    'username': target_username,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                # Keep cache in sync
                if self._cached_following is not None and target_username not in self._cached_following:
                    self._cached_following.append(target_username)
                return True, f"Successfully followed @{target_username}! 🤝"
            elif response.status_code == 404:
                return False, f"User @{target_username} not found ❌"
            elif response.status_code == 403:
                rate_response = self.session.get(f"{self.api_url}/rate_limit")
                if rate_response.status_code == 200:
                    rate_data = rate_response.json()
                    remaining  = rate_data['resources']['core']['remaining']
                    reset_time = rate_data['resources']['core']['reset']
                    if remaining == 0:
                        wait_time = datetime.fromtimestamp(reset_time) - datetime.now()
                        return False, f"Rate limited! Try again in {wait_time.seconds // 60} minutes ⏳"
                return False, "Forbidden - Check your token permissions 🔐"
            elif response.status_code == 401:
                return False, "Unauthorized - Token may have expired 🔐"
            else:
                return False, f"Follow failed: HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"Follow error: {e}")
            return False, f"Follow error: {str(e)}"
    
    def unfollow_user(self, target_username: str) -> Tuple[bool, str]:
        try:
            if not self.username or not self.access_token:
                return False, "Please login with access token first!"
            self.animate_loading(f"Preparing to unfollow @{target_username}")
            time.sleep(random.uniform(1, 3))
            response = self.session.delete(f"{self.api_url}/user/following/{target_username}")
            if response.status_code == 204:
                self.followed_users = [u for u in self.followed_users if u['username'] != target_username]
                # Keep cache in sync
                if self._cached_following is not None and target_username in self._cached_following:
                    self._cached_following.remove(target_username)
                return True, f"Successfully unfollowed @{target_username}! 👋"
            elif response.status_code == 404:
                return False, f"User @{target_username} not found ❌"
            elif response.status_code == 403:
                return False, "Forbidden - Check your token permissions 🔐"
            else:
                return False, f"Unfollow failed: HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"Unfollow error: {e}")
            return False, f"Unfollow error: {str(e)}"
    
    def star_repository(self, repo_owner: str, repo_name: str) -> Tuple[bool, str]:
        try:
            if not self.username or not self.access_token:
                return False, "Please login with access token first!"
            self.animate_loading(f"Preparing to star {repo_owner}/{repo_name}")
            time.sleep(random.uniform(1, 3))
            response = self.session.put(f"{self.api_url}/user/starred/{repo_owner}/{repo_name}")
            if response.status_code == 204:
                self.starred_repos.append({
                    'owner': repo_owner, 'repo': repo_name,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                return True, f"Successfully starred {repo_owner}/{repo_name}! ⭐"
            elif response.status_code == 404:
                return False, f"Repository {repo_owner}/{repo_name} not found ❌"
            else:
                return False, f"Star failed: HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"Star error: {e}")
            return False, f"Star error: {str(e)}"
    
    def fork_repository(self, repo_owner: str, repo_name: str) -> Tuple[bool, str]:
        try:
            if not self.username or not self.access_token:
                return False, "Please login with access token first!"
            self.animate_loading(f"Preparing to fork {repo_owner}/{repo_name}")
            time.sleep(random.uniform(2, 5))
            response = self.session.post(f"{self.api_url}/repos/{repo_owner}/{repo_name}/forks", json={})
            if response.status_code == 202:
                fork_url = response.json().get('html_url', '')
                return True, f"Successfully forked repository! 🍴\nFork URL: {fork_url}"
            elif response.status_code == 403:
                check = self.session.get(f"{self.api_url}/repos/{repo_owner}/{repo_name}")
                if check.status_code == 200 and check.json().get('fork'):
                    return False, "Repository is already a fork"
                return False, "Forbidden - Check your token permissions or repository visibility 🔐"
            elif response.status_code == 404:
                return False, f"Repository {repo_owner}/{repo_name} not found ❌"
            else:
                return False, f"Fork failed: HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"Fork error: {e}")
            return False, f"Fork error: {str(e)}"
    
    def get_repository_info(self, repo_owner: str, repo_name: str) -> Optional[Dict]:
        try:
            self.animate_loading(f"Fetching info for {repo_owner}/{repo_name}")
            response = self.session.get(f"{self.api_url}/repos/{repo_owner}/{repo_name}")
            if response.status_code == 200:
                repo_data = response.json()
                languages, contributors = {}, []
                if repo_data.get('languages_url'):
                    lr = self.session.get(repo_data['languages_url'])
                    if lr.status_code == 200:
                        languages = lr.json()
                if repo_data.get('contributors_url'):
                    cr = self.session.get(repo_data['contributors_url'] + "?per_page=10")
                    if cr.status_code == 200:
                        contributors = cr.json()[:5]
                return {
                    'name': repo_data.get('name'),
                    'full_name': repo_data.get('full_name'),
                    'owner': repo_data.get('owner', {}).get('login'),
                    'description': repo_data.get('description'),
                    'language': repo_data.get('language'),
                    'languages': languages,
                    'stars': repo_data.get('stargazers_count', 0),
                    'watchers': repo_data.get('watchers_count', 0),
                    'forks': repo_data.get('forks_count', 0),
                    'open_issues': repo_data.get('open_issues_count', 0),
                    'license': repo_data.get('license', {}).get('name'),
                    'created_at': repo_data.get('created_at'),
                    'updated_at': repo_data.get('updated_at'),
                    'pushed_at': repo_data.get('pushed_at'),
                    'homepage': repo_data.get('homepage'),
                    'topics': repo_data.get('topics', []),
                    'contributors': contributors,
                    'size': repo_data.get('size', 0),
                    'default_branch': repo_data.get('default_branch'),
                    'archived': repo_data.get('archived', False),
                    'fork': repo_data.get('fork', False)
                }
            return None
        except Exception as e:
            logger.error(f"Error getting repo info: {e}")
            return None

    # ──────────────────────────────────────────────────────────────────
    # OPTIMIZATION: single generic paginated fetcher reused everywhere.
    # Rate-limit check only every 5 pages (was every page → −80% calls).
    # Page sleep reduced from 0.5 s → 0.3 s.
    # ──────────────────────────────────────────────────────────────────
    def _fetch_paginated_users(self, url_template: str, label: str,
                                max_users: int = 2500) -> List[str]:
        """
        Page through a GitHub list endpoint.
        url_template must contain {page} and {per_page} placeholders.
        """
        users: List[str] = []
        page = 1
        per_page = 100

        while True:
            url = url_template.format(page=page, per_page=per_page)
            response = self.session.get(url)

            if response.status_code == 200:
                data = response.json()
                if not data:
                    break
                users.extend(u['login'] for u in data)
                self.print_info(f"Loaded {len(users)} {label} so far...")

                # Only check rate limit every 5 pages
                if page % 5 == 0:
                    self._check_rate_limit_low(50)

                page += 1
                time.sleep(0.3)

                if len(users) >= max_users:
                    self.print_warning(f"Reached safety limit of {max_users} {label}")
                    break

            elif response.status_code == 403:
                self.print_error(f"Rate limited while fetching {label}")
                break
            elif response.status_code == 404:
                self.print_error(f"User not found while fetching {label}")
                break
            else:
                self.print_error(f"Failed to fetch {label}: HTTP {response.status_code}")
                break

        return users

    # ──────────────────────────────────────────────────────────────────
    # Seed-user follower fetcher (single user)
    # ──────────────────────────────────────────────────────────────────
    def get_followers_for_user(self, username: str,
                                max_followers: int = 2500) -> List[str]:
        """Get all followers of a specific user."""
        try:
            self.print_info(f"Fetching followers for @{username}...")
            url_tpl = (f"{self.api_url}/users/{username}/followers"
                       "?page={page}&per_page={per_page}")
            return self._fetch_paginated_users(
                url_tpl, f"followers of @{username}", max_followers)
        except Exception as e:
            self.print_error(f"Error getting followers for @{username}: {str(e)}")
            return []

    # ──────────────────────────────────────────────────────────────────
    # OPTIMIZATION: fetch multiple seed users' followers IN PARALLEL
    # ──────────────────────────────────────────────────────────────────
    def get_followers_for_users_parallel(self, seed_users: List[str],
                                          max_followers: int = 2500,
                                          max_workers: int = 4
                                          ) -> Dict[str, List[str]]:
        """
        Fetch followers for all seed users concurrently.
        4 workers is safe against GitHub secondary rate limits.
        Returns {seed_username: [follower, ...]}
        """
        results: Dict[str, List[str]] = {}

        def _fetch(uname):
            return uname, self.get_followers_for_user(uname, max_followers)

        self.print_info(
            f"Fetching followers for {len(seed_users)} seed users in parallel…")

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for uname, followers in (f.result() for f in as_completed(
                    {ex.submit(_fetch, u): u for u in seed_users})):
                results[uname] = followers
                self.print_success(
                    f"Finished @{uname}: {len(followers)} followers fetched")

        return results

    # ──────────────────────────────────────────────────────────────────
    # Seed-follower extraction flow  ← MAIN LOGIC CHANGE
    # ──────────────────────────────────────────────────────────────────
    def handle_seed_follower_extractor_flow(self):
        """Handle the seed user follower extraction flow."""
        if not self.username or not self.access_token:
            self.print_error("Please login with access token first!")
            return
        
        self.print_header("SEED USER FOLLOWER EXTRACTOR")
        
        print(f"\n{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}✨ Instructions ✨{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}")
        print(f"{Colors.BRIGHT_WHITE}• Enter seed usernames (1-5 users)")
        print(f"• Type 'done' when finished")
        print(f"• Users you already follow will be filtered out automatically")
        print(f"• Followers will be combined into one unique list")
        print(f"• You can then choose to follow the entire filtered list{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}\n")
        
        # ── STEP 1: collect seed usernames ────────────────────────────
        seed_users: List[str] = []
        print(f"{Colors.BRIGHT_GREEN}[1/4]{Colors.RESET} {Colors.BRIGHT_WHITE}Enter Seed Users{Colors.RESET}\n")
        
        while True:
            if len(seed_users) >= 5:
                self.print_info("Maximum of 5 seed users reached.")
                choice = self.get_input(
                    "Type 'done' to continue or 'list' to see current users: ")
                if choice.lower() == 'done':
                    break
                elif choice.lower() == 'list':
                    self.display_seed_users(seed_users)
                continue

            username = self.get_input(
                f"Seed user {len(seed_users) + 1} (or 'done' when finished): ").strip()

            if username.lower() == 'done':
                if not seed_users:
                    self.print_warning("Please enter at least one seed user!")
                    continue
                break
            elif username.lower() == 'list':
                self.display_seed_users(seed_users)
            elif username.lower() == 'clear':
                seed_users = []
                self.print_success("List cleared!")
            elif not username:
                self.print_warning("Username cannot be empty!")
            elif username in seed_users:
                self.print_warning(f"@{username} is already in the list!")
            elif not self.verify_user_exists(username):
                self.print_warning(f"@{username} doesn't seem to exist!")
            else:
                seed_users.append(username)
                self.print_success(f"Added @{username} to seed users list")

        # ── STEP 2: fetch YOUR current following list (with cache) ────
        print(f"\n{Colors.BRIGHT_GREEN}[2/4]{Colors.RESET} "
              f"{Colors.BRIGHT_WHITE}Loading Your Following List (for filtering){Colors.RESET}\n")
        your_following     = self._get_following_cached()
        your_following_set = set(your_following)
        self.print_success(
            f"You currently follow {len(your_following_set)} users — "
            "these will be filtered out automatically.")

        # ── STEP 3: extract followers (parallel when multiple seeds) ──
        print(f"\n{Colors.BRIGHT_GREEN}[3/4]{Colors.RESET} "
              f"{Colors.BRIGHT_WHITE}Extracting Followers{Colors.RESET}\n")

        if len(seed_users) > 1:
            per_user_followers = self.get_followers_for_users_parallel(seed_users)
        else:
            per_user_followers = {
                seed_users[0]: self.get_followers_for_user(seed_users[0])}

        # Merge and build source map
        all_followers: List[str] = []
        follower_sources: Dict[str, List[str]] = {}

        for seed_user in seed_users:
            followers = per_user_followers.get(seed_user, [])
            for follower in followers:
                follower_sources.setdefault(follower, []).append(seed_user)
            new = [f for f in followers if f not in all_followers]
            all_followers.extend(new)
            self.print_success(
                f"@{seed_user}: {len(followers)} followers "
                f"({len(new)} new unique)")

        # ── KEY FIX: remove users you already follow ──────────────────
        already_following_count = sum(
            1 for f in all_followers if f in your_following_set)
        filtered_followers = [
            f for f in all_followers
            if f not in your_following_set and f != self.username
        ]

        print(f"\n{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}✨ Filtering Summary ✨{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}")
        self.print_info   (f"Total extracted (raw):       {len(all_followers)}")
        self.print_warning(f"Already following (removed): {already_following_count}")
        self.print_success(f"New users to follow:         {len(filtered_followers)}")

        # ── STEP 4: display & act ─────────────────────────────────────
        print(f"\n{Colors.BRIGHT_GREEN}[4/4]{Colors.RESET} "
              f"{Colors.BRIGHT_WHITE}Results Summary{Colors.RESET}\n")
        self.display_follower_extraction_results(
            seed_users, filtered_followers, follower_sources)
        
        print(f"\n{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}✨ Follow Options ✨{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}")
        
        if not filtered_followers:
            self.print_error("No new followers to follow after filtering!")
            return
        
        print(f"\n{Colors.BRIGHT_WHITE}Would you like to follow the filtered followers?{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}[1]{Colors.RESET} {Colors.BRIGHT_WHITE}Follow all {len(filtered_followers)} new followers{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}[2]{Colors.RESET} {Colors.BRIGHT_WHITE}Follow a specific number of followers{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}[3]{Colors.RESET} {Colors.BRIGHT_WHITE}Save followers to a file{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}[4]{Colors.RESET} {Colors.BRIGHT_WHITE}Exit without following{Colors.RESET}")
        
        choice = self.get_input("\nSelect option (1-4)")
        
        if choice == '1':
            self.follow_extracted_followers(filtered_followers)
        elif choice == '2':
            max_follow = self.get_input(
                f"How many followers to follow? (1-{len(filtered_followers)}): ")
            try:
                max_follow = max(1, min(int(max_follow), len(filtered_followers)))
                self.follow_extracted_followers(filtered_followers[:max_follow])
            except ValueError:
                self.print_error("Invalid number!")
        elif choice == '3':
            self.save_followers_to_file(filtered_followers, seed_users)
        elif choice == '4':
            self.print_info("Exiting without following.")
        else:
            self.print_error("Invalid option!")
    
    def display_seed_users(self, seed_users: List[str]):
        if not seed_users:
            self.print_info("No seed users added yet.")
            return
        print(f"\n{Colors.BRIGHT_GREEN}Current Seed Users ({len(seed_users)}):{Colors.RESET}")
        for i, user in enumerate(seed_users, 1):
            print(f"  {Colors.BRIGHT_YELLOW}{i}.{Colors.RESET} @{user}")
    
    def display_follower_extraction_results(self, seed_users: List[str],
                                             all_followers: List[str],
                                             follower_sources: Dict):
        print(f"{Colors.BRIGHT_GREEN}┌────────────────────────────────────────────────────────────┐{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.BRIGHT_CYAN}            Follower Extraction Results              {Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}├────────────────────────────────────────────────────────────┤{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_WHITE}Seed Users:{Colors.RESET} {len(seed_users):>2}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_WHITE}New Unique Followers (filtered):{Colors.RESET} {len(all_followers):>2}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}└────────────────────────────────────────────────────────────┘{Colors.RESET}")
        
        print(f"\n{Colors.BRIGHT_CYAN}{'─' * 40}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}Seed User Breakdown{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─' * 40}{Colors.RESET}")
        for i, seed_user in enumerate(seed_users, 1):
            c = sum(1 for s in follower_sources.values() if seed_user in s)
            print(f"{Colors.BRIGHT_YELLOW}{i}.{Colors.RESET} @{seed_user:<20} {Colors.BRIGHT_WHITE}{c:>3} followers{Colors.RESET}")
        
        print(f"\n{Colors.BRIGHT_CYAN}{'─' * 40}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}Follower Overlap Analysis{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─' * 40}{Colors.RESET}")
        overlap_stats: Dict[int, int] = {}
        for sources in follower_sources.values():
            n = len(sources)
            overlap_stats[n] = overlap_stats.get(n, 0) + 1
        for n in sorted(overlap_stats, reverse=True):
            cnt = overlap_stats[n]
            pct = (cnt / len(all_followers) * 100) if all_followers else 0
            label = f"{n} seed user{'s' if n > 1 else ''}"
            print(f"{Colors.BRIGHT_YELLOW}{n}.{Colors.RESET} {Colors.BRIGHT_WHITE}{cnt:>3} followers{Colors.RESET} from {label} ({pct:.1f}%)")
        
        if all_followers:
            print(f"\n{Colors.BRIGHT_CYAN}{'─' * 40}{Colors.RESET}")
            print(f"{Colors.BRIGHT_MAGENTA}Sample of New Followers (First 20){Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}{'─' * 40}{Colors.RESET}")
            for i, follower in enumerate(all_followers[:20], 1):
                sources = follower_sources.get(follower, [])
                src_txt = f"(from: {', '.join(f'@{s}' for s in sources)})" if sources else ""
                print(f"{Colors.BRIGHT_YELLOW}{i:2}.{Colors.RESET} @{follower:<20} {Colors.DIM}{src_txt}{Colors.RESET}")
            if len(all_followers) > 20:
                print(f"{Colors.DIM}... and {len(all_followers) - 20} more{Colors.RESET}")
    
    def follow_extracted_followers(self, followers_to_follow: List[str]):
        if not followers_to_follow:
            self.print_error("No followers to follow!")
            return
        print(f"\n{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}✨ Follow Configuration ✨{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}")
        min_delay = self.get_input("Minimum delay between follows (seconds, 10-30 recommended): ")
        max_delay = self.get_input("Maximum delay between follows (seconds, 10-30 recommended): ")
        try:
            min_delay = int(min_delay) if min_delay else 10
            max_delay = int(max_delay) if max_delay else 30
            min_delay = max(1, min_delay)
            if max_delay < min_delay:
                max_delay = min_delay + 5
            max_delay = min(300, max_delay)
            print(f"\n{Colors.BRIGHT_WHITE}Follow Summary:{Colors.RESET}")
            print(f"{Colors.BRIGHT_YELLOW}• Total to follow:{Colors.RESET} {len(followers_to_follow)}")
            print(f"{Colors.BRIGHT_YELLOW}• Delay range:{Colors.RESET} {min_delay}-{max_delay} seconds")
            print(f"{Colors.BRIGHT_YELLOW}• Estimated time:{Colors.RESET} "
                  f"{len(followers_to_follow) * ((min_delay + max_delay) / 2) / 60:.1f} minutes")
            print(f"{Colors.BRIGHT_YELLOW}• Your account:{Colors.RESET} @{self.username}")
            print(f"\n{Colors.BRIGHT_RED}{'!' * 60}{Colors.RESET}")
            print(f"{Colors.BRIGHT_RED}{Colors.BOLD}⚠️  IMPORTANT WARNING:{Colors.RESET}")
            print(f"{Colors.BRIGHT_RED}{'!' * 60}{Colors.RESET}")
            print(f"{Colors.BRIGHT_YELLOW}• Following many users may look suspicious{Colors.RESET}")
            print(f"{Colors.BRIGHT_YELLOW}• GitHub may temporarily limit your account{Colors.RESET}")
            print(f"{Colors.BRIGHT_YELLOW}• Recommended: Follow max 50 users per session{Colors.RESET}")
            confirm = self.get_input(
                f"\nAre you SURE you want to follow {len(followers_to_follow)} users? (y/N): ").lower()
            if confirm == 'y':
                self.bulk_follow_extracted_users(followers_to_follow, min_delay, max_delay)
            else:
                self.print_info("Follow operation cancelled")
        except ValueError:
            self.print_error("Invalid delay values!")
    
    def bulk_follow_extracted_users(self, usernames: List[str],
                                     min_delay: int = 10, max_delay: int = 30):
        results = {'successful': [], 'failed': [], 'total': len(usernames)}
        self.print_header("FOLLOWING EXTRACTED FOLLOWERS")
        print(f"{Colors.BRIGHT_CYAN}📋 Following {len(usernames)} users "
              f"with {min_delay}-{max_delay}s delay{Colors.RESET}\n")
        for i, username in enumerate(usernames, 1):
            print(f"\n{Colors.BRIGHT_CYAN}[{i}/{len(usernames)}]{Colors.RESET} Processing @{username}")
            success, message = self.follow_user(username)
            if success:
                self.print_success(f"Followed @{username}")
                results['successful'].append({'username': username, 'message': message})
            else:
                self.print_error(f"Failed @{username}: {message}")
                results['failed'].append({'username': username, 'message': message})
            if i < len(usernames):
                delay = random.randint(min_delay, max_delay)
                print(f"{Colors.DIM}Waiting {delay}s...{Colors.RESET}")
                for sec in range(delay, 0, -1):
                    sys.stdout.write(f"\r{Colors.DIM}Next follow in {sec}s...{' '*10}{Colors.RESET}")
                    sys.stdout.flush()
                    time.sleep(1)
                sys.stdout.write('\r' + ' ' * 40 + '\r')
        self.print_header("FOLLOW RESULTS")
        total = results['total']
        print(f"{Colors.BRIGHT_GREEN}┌────────────────────────────────────────────────────────────┐{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_GREEN}✅ Successful:{Colors.RESET} {len(results['successful']):>3}/{total}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_RED}❌ Failed:{Colors.RESET}     {len(results['failed']):>3}/{total}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_CYAN}📊 Success Rate:{Colors.RESET} "
              f"{len(results['successful'])/total*100:>6.1f}%{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}└────────────────────────────────────────────────────────────┘{Colors.RESET}")
        if results['failed']:
            print(f"\n{Colors.BRIGHT_YELLOW}Failed users (first 10):{Colors.RESET}")
            for fail in results['failed'][:10]:
                print(f"  {Colors.DIM}@{fail['username']}: {fail['message']}{Colors.RESET}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"github_follow_results_{timestamp}.txt"
        with open(filename, 'w') as f:
            f.write(f"GitHub Follow Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total attempted: {total}\n")
            f.write(f"Successful: {len(results['successful'])}\n")
            f.write(f"Failed: {len(results['failed'])}\n")
            f.write(f"Success rate: {len(results['successful'])/total*100:.1f}%\n\n")
            f.write("Successful follows:\n")
            for s in results['successful']:
                f.write(f"@{s['username']}\n")
            f.write("\nFailed follows:\n")
            for fail in results['failed']:
                f.write(f"@{fail['username']}: {fail['message']}\n")
        self.print_success(f"Results saved to: {filename}")
    
    def save_followers_to_file(self, followers: List[str], seed_users: List[str]):
        if not followers:
            self.print_error("No followers to save!")
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"github_followers_{timestamp}.txt"
        with open(filename, 'w') as f:
            f.write(f"GitHub Followers Extracted - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Seed Users: {', '.join(f'@{u}' for u in seed_users)}\n")
            f.write(f"Total unique new followers: {len(followers)}\n")
            f.write("(Users already followed have been filtered out)\n\n")
            f.write("Extracted Followers:\n")
            for i, follower in enumerate(followers, 1):
                f.write(f"{i}. @{follower}\n")
        self.print_success(f"Saved {len(followers)} followers to: {filename}")

    # ──────────────────────────────────────────────────────────────────
    # OPTIMIZATION: cached following list — fetched once, reused by
    # both the seed-follower extractor and the followback cleaner.
    # ──────────────────────────────────────────────────────────────────
    def _get_following_cached(self) -> List[str]:
        """
        Return the logged-in user's following list.
        Fetches from API once per session, then reuses the in-memory cache.
        """
        if self._cached_following is not None:
            self.print_info(
                "Using cached following list (already fetched this session).")
            return self._cached_following
        self._cached_following = self.get_all_following()
        return self._cached_following

    def get_all_followers(self) -> List[str]:
        try:
            if not self.username or not self.access_token:
                self.print_error("Please login first!")
                return []
            self.print_info("Fetching your followers...")
            url_tpl = (f"{self.api_url}/users/{self.username}/followers"
                       "?page={page}&per_page={per_page}")
            return self._fetch_paginated_users(url_tpl, "followers", 2000)
        except Exception as e:
            self.print_error(f"Error getting followers: {str(e)}")
            return []
    
    def get_all_following(self) -> List[str]:
        try:
            if not self.username or not self.access_token:
                self.print_error("Please login first!")
                return []
            self.print_info("Fetching users you're following...")
            url_tpl = (f"{self.api_url}/users/{self.username}/following"
                       "?page={page}&per_page={per_page}")
            return self._fetch_paginated_users(url_tpl, "following", 2000)
        except Exception as e:
            self.print_error(f"Error getting following: {str(e)}")
            return []
    
    def check_follow_back_status(self) -> Tuple[List[str], List[str], List[str]]:
        try:
            self.print_header("FOLLOWBACK ANALYSIS")
            self.animate_loading("Loading your followers list", 2)
            followers = self.get_all_followers()
            self.animate_loading("Loading users you follow", 2)
            # OPTIMIZATION: reuse cached following list
            following = self._get_following_cached()
            if not followers or not following:
                self.print_error("Could not fetch follow data")
                return [], [], []
            followers_set = set(followers)
            following_set = set(following)
            mutual           = sorted(followers_set & following_set)
            not_following_back = sorted(following_set - followers_set)
            fans             = sorted(followers_set - following_set)
            return mutual, not_following_back, fans
        except Exception as e:
            self.print_error(f"Error in followback check: {str(e)}")
            return [], [], []
    
    def display_followback_analysis(self, mutual: List[str],
                                     not_following_back: List[str],
                                     fans: List[str]):
        print(f"\n{Colors.BRIGHT_CYAN}{'═' * 60}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}📊 FOLLOWBACK ANALYSIS RESULTS{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'═' * 60}{Colors.RESET}")
        print(f"\n{Colors.BRIGHT_GREEN}┌────────────────────────────────────────────────────────────┐{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.BRIGHT_CYAN}                    Summary Statistics                    {Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}├────────────────────────────────────────────────────────────┤{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_WHITE}Your Followers:{Colors.RESET} {len(mutual)+len(fans):>4}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_WHITE}You're Following:{Colors.RESET} {len(mutual)+len(not_following_back):>3}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_WHITE}Mutual Followers:{Colors.RESET} {len(mutual):>3}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_WHITE}Don't Follow Back:{Colors.RESET} {len(not_following_back):>3}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_WHITE}Fans (You don't follow back):{Colors.RESET} {len(fans):>3}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}└────────────────────────────────────────────────────────────┘{Colors.RESET}")
        
        if not_following_back:
            print(f"\n{Colors.BRIGHT_RED}{'─' * 60}{Colors.RESET}")
            print(f"{Colors.BRIGHT_RED}{Colors.BOLD}❌ USERS WHO DON'T FOLLOW YOU BACK ({len(not_following_back)}){Colors.RESET}")
            print(f"{Colors.BRIGHT_RED}{'─' * 60}{Colors.RESET}")
            cols = 3
            rows = (len(not_following_back) + cols - 1) // cols
            for i in range(rows):
                line = ""
                for j in range(cols):
                    idx = i + j * rows
                    if idx < len(not_following_back):
                        line += (f"{Colors.BRIGHT_YELLOW}{idx+1:3}.{Colors.RESET} "
                                 f"{Colors.BRIGHT_RED}@{not_following_back[idx]:<20}{Colors.RESET}")
                if line:
                    print(line)
            total_following = len(mutual) + len(not_following_back)
            if total_following > 0:
                ratio = len(mutual) / total_following * 100
                print(f"\n{Colors.BRIGHT_CYAN}📈 Follow-back Ratio: {ratio:.1f}%{Colors.RESET}")
                if ratio < 30:
                    self.print_warning("⚠️  Your follow-back ratio is very low!")
                elif ratio < 50:
                    self.print_warning("⚠️  Your follow-back ratio is low.")
                elif ratio > 70:
                    self.print_success("✅ Great follow-back ratio!")
        
        if mutual:
            print(f"\n{Colors.BRIGHT_GREEN}{'─' * 60}{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}🤝 MUTUAL FOLLOWERS ({len(mutual)}){Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}{'─' * 60}{Colors.RESET}")
            for i, u in enumerate(mutual[:20], 1):
                print(f"{Colors.BRIGHT_YELLOW}{i:3}.{Colors.RESET} {Colors.BRIGHT_GREEN}@{u}{Colors.RESET}")
            if len(mutual) > 20:
                print(f"{Colors.DIM}... and {len(mutual)-20} more{Colors.RESET}")
        
        if fans:
            print(f"\n{Colors.BRIGHT_BLUE}{'─' * 60}{Colors.RESET}")
            print(f"{Colors.BRIGHT_BLUE}{Colors.BOLD}⭐ FANS ({len(fans)}) - They follow you{Colors.RESET}")
            print(f"{Colors.BRIGHT_BLUE}{'─' * 60}{Colors.RESET}")
            for i, u in enumerate(fans[:15], 1):
                print(f"{Colors.BRIGHT_YELLOW}{i:3}.{Colors.RESET} {Colors.BRIGHT_BLUE}@{u}{Colors.RESET}")
            if len(fans) > 15:
                print(f"{Colors.DIM}... and {len(fans)-15} more fans{Colors.RESET}")
        
        print(f"\n{Colors.BRIGHT_CYAN}{'═' * 60}{Colors.RESET}")
    
    def bulk_unfollow_non_followers(self, usernames: List[str],
                                     delay: int = 10) -> Dict:
        results = {'successful': [], 'failed': [], 'total': len(usernames)}
        self.print_header("BULK UNFOLLOW OPERATION")
        print(f"{Colors.BRIGHT_CYAN}📋 Unfollowing {len(usernames)} users with {delay}s delay{Colors.RESET}\n")
        print(f"{Colors.BRIGHT_YELLOW}⚠️  Warning: Use responsibly!{Colors.RESET}\n")
        for i, username in enumerate(usernames, 1):
            print(f"\n{Colors.BRIGHT_CYAN}[{i}/{len(usernames)}]{Colors.RESET} Unfollowing @{username}")
            success, message = self.unfollow_user(username)
            if success:
                self.print_success(f"Unfollowed @{username}")
                results['successful'].append({'username': username, 'message': message})
            else:
                self.print_error(f"Failed @{username}: {message}")
                results['failed'].append({'username': username, 'message': message})
            if i < len(usernames):
                print(f"{Colors.DIM}Waiting {delay}s...{Colors.RESET}")
                for sec in range(delay, 0, -1):
                    sys.stdout.write(f"\r{Colors.DIM}Next unfollow in {sec}s...{Colors.RESET}")
                    sys.stdout.flush()
                    time.sleep(1)
                sys.stdout.write('\r' + ' ' * 30 + '\r')
        return results
    
    def handle_followback_cleaner_flow(self):
        if not self.username or not self.access_token:
            self.print_error("Please login with access token first!")
            return
        self.print_header("FOLLOWBACK CLEANER")
        while True:
            print(f"\n{Colors.BRIGHT_CYAN}{'─' * 50}{Colors.RESET}")
            print(f"{Colors.BRIGHT_MAGENTA}✨ Followback Cleaner Options ✨{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}{'─' * 50}{Colors.RESET}\n")
            print(f"{Colors.BRIGHT_GREEN}[1]{Colors.RESET} {Colors.BRIGHT_WHITE}Check who doesn't follow back{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}[2]{Colors.RESET} {Colors.BRIGHT_WHITE}Unfollow users who don't follow back{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}[3]{Colors.RESET} {Colors.BRIGHT_WHITE}Back to main menu{Colors.RESET}")
            choice = self.get_input("\nSelect option (1-3)")
            
            if choice == '1':
                mutual, nfb, fans = self.check_follow_back_status()
                if nfb or mutual or fans:
                    self.display_followback_analysis(mutual, nfb, fans)
                    if nfb:
                        print(f"\n{Colors.BRIGHT_YELLOW}Found {len(nfb)} users who don't follow you back!{Colors.RESET}")
                        print(f"{Colors.BRIGHT_WHITE}Use option 2 to unfollow them.{Colors.RESET}")
                else:
                    self.print_error("No follow data available or error in analysis")
            
            elif choice == '2':
                self.print_info("Checking who doesn't follow you back...")
                mutual, nfb, fans = self.check_follow_back_status()
                if not nfb:
                    self.print_success("Everyone you follow follows you back! 🎉")
                    continue
                self.display_followback_analysis(mutual, nfb, fans)
                print(f"\n{Colors.BRIGHT_RED}{'!' * 60}{Colors.RESET}")
                print(f"{Colors.BRIGHT_RED}{Colors.BOLD}⚠️  IMPORTANT WARNING:{Colors.RESET}")
                print(f"{Colors.BRIGHT_RED}{'!' * 60}{Colors.RESET}")
                print(f"{Colors.BRIGHT_YELLOW}• Unfollowing many users may look suspicious{Colors.RESET}")
                print(f"{Colors.BRIGHT_YELLOW}• GitHub may temporarily limit your account{Colors.RESET}")
                print(f"{Colors.BRIGHT_YELLOW}• Recommended: Unfollow max 50 users per session{Colors.RESET}")
                print(f"\n{Colors.BRIGHT_WHITE}Select unfollow option:{Colors.RESET}")
                print(f"{Colors.BRIGHT_GREEN}[1]{Colors.RESET} {Colors.BRIGHT_WHITE}Unfollow ALL ({len(nfb)} users){Colors.RESET}")
                print(f"{Colors.BRIGHT_GREEN}[2]{Colors.RESET} {Colors.BRIGHT_WHITE}Unfollow first 50 only{Colors.RESET}")
                print(f"{Colors.BRIGHT_GREEN}[3]{Colors.RESET} {Colors.BRIGHT_WHITE}Select specific users{Colors.RESET}")
                print(f"{Colors.BRIGHT_GREEN}[4]{Colors.RESET} {Colors.BRIGHT_WHITE}Cancel{Colors.RESET}")
                uc = self.get_input("\nSelect option (1-4)")
                users_to_unfollow: List[str] = []
                if uc == '1':
                    users_to_unfollow = nfb
                elif uc == '2':
                    users_to_unfollow = nfb[:50]
                elif uc == '3':
                    print(f"\n{Colors.BRIGHT_WHITE}Enter usernames to unfollow (type 'done' when finished):{Colors.RESET}")
                    print(f"{Colors.DIM}Available: {', '.join(nfb[:20])}{Colors.RESET}")
                    selected: List[str] = []
                    while True:
                        u = self.get_input("Username (or 'done'): ").strip()
                        if u.lower() == 'done':
                            break
                        if u in nfb and u not in selected:
                            selected.append(u)
                            self.print_success(f"Added @{u}")
                        elif u in selected:
                            self.print_warning(f"@{u} already in list")
                        else:
                            self.print_warning(f"@{u} not in non-followers list")
                    users_to_unfollow = selected
                elif uc == '4':
                    continue
                else:
                    self.print_error("Invalid option!")
                    continue
                
                if not users_to_unfollow:
                    self.print_warning("No users selected")
                    continue
                
                print(f"\n{Colors.BRIGHT_WHITE}Users to unfollow ({len(users_to_unfollow)}):{Colors.RESET}")
                for i, u in enumerate(users_to_unfollow[:10], 1):
                    print(f"  {Colors.BRIGHT_YELLOW}{i}.{Colors.RESET} @{u}")
                if len(users_to_unfollow) > 10:
                    print(f"  {Colors.DIM}... and {len(users_to_unfollow)-10} more{Colors.RESET}")
                
                delay = int(self.get_input(
                    "\nDelay between unfollows (seconds, recommended 10-30): ") or "15")
                confirm = self.get_input(
                    f"\nUnfollow {len(users_to_unfollow)} users? (y/N): ").lower()
                
                if confirm == 'y':
                    results = self.bulk_unfollow_non_followers(users_to_unfollow, delay)
                    self.print_header("UNFOLLOW RESULTS")
                    total = results['total']
                    print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} ✅ Successful: {len(results['successful'])}/{total}{Colors.RESET}")
                    print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} ❌ Failed:     {len(results['failed'])}/{total}{Colors.RESET}")
                    if results['failed']:
                        for fail in results['failed'][:5]:
                            print(f"  {Colors.DIM}@{fail['username']}: {fail['message']}{Colors.RESET}")
                else:
                    self.print_info("Unfollow operation cancelled")
            
            elif choice == '3':
                break
            else:
                self.print_error("Invalid option! Please choose 1-3.")
            
            input(f"\n{Colors.BRIGHT_WHITE}Press Enter to continue...{Colors.RESET}")
            self.clear_screen()
            self.print_banner()
    
    def display_user_statistics(self, user_info: Dict):
        if not user_info:
            self.print_error("No user information available")
            return
        self.print_header("GITHUB PROFILE ANALYTICS")
        print(f"{Colors.BRIGHT_GREEN}┌────────────────────────────────────────────────────────────┐{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.BRIGHT_MAGENTA}{Colors.BOLD}👤 PROFILE INFORMATION{Colors.RESET:<41}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}├────────────────────────────────────────────────────────────┤{Colors.RESET}")
        username_display = f"@{user_info.get('username','N/A')}"
        if user_info.get('name'):
            username_display += f" • {user_info['name']}"
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_CYAN}GitHub:{Colors.RESET} {Colors.BRIGHT_WHITE}{username_display:<48}{Colors.RESET}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        if user_info.get('company'):
            print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_CYAN}Company:{Colors.RESET} {Colors.BRIGHT_YELLOW}{user_info['company']:<48}{Colors.RESET}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        if user_info.get('location'):
            print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_CYAN}Location:{Colors.RESET} {Colors.BRIGHT_YELLOW}{user_info['location']:<48}{Colors.RESET}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}└────────────────────────────────────────────────────────────┘{Colors.RESET}")
        print(f"\n{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}📊 PROFILE STATISTICS{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─' * 60}{Colors.RESET}\n")
        print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
        for label, key in [('👥 Followers','followers'),('🤝 Following','following'),
                            ('📂 Public Repos','public_repos'),('📝 Public Gists','public_gists'),
                            ('⭐ Total Stars','total_stars'),('🍴 Total Forks','total_forks')]:
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} "
                  f"{Colors.BRIGHT_MAGENTA}{label}:{Colors.RESET} "
                  f"{Colors.BRIGHT_WHITE}{user_info.get(key,0):,}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
        repos = user_info.get('public_repos', 0)
        top_languages = user_info.get('top_languages', [])
        if top_languages:
            print(f"\n{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}")
            print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}💻 TOP PROGRAMMING LANGUAGES{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}\n")
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
            for lang, count in top_languages[:5]:
                pct = (count / repos * 100) if repos > 0 else 0
                bar = '█' * int(pct/5) + '░' * (20 - int(pct/5))
                print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} "
                      f"{Colors.BRIGHT_CYAN}{lang:<15}{Colors.RESET} "
                      f"{Colors.BRIGHT_WHITE}{bar}{Colors.RESET} "
                      f"{Colors.BRIGHT_MAGENTA}{pct:.1f}%{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
        if user_info.get('bio'):
            bio = user_info['bio'][:147] + "..." if len(user_info['bio']) > 150 else user_info['bio']
            print(f"\n{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}")
            print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}📝 BIOGRAPHY{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}\n")
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
            for line in self.wrap_text(bio, 38):
                print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} {Colors.BRIGHT_CYAN}{line:<35}{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
        print(f"\n{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}🔗 ADDITIONAL INFORMATION{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}\n")
        info_count = 0
        print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
        for label, key in [('Website','blog'),('Twitter','twitter'),('Email','email')]:
            if user_info.get(key):
                val = (f"@{user_info[key]}" if key == 'twitter' else user_info[key])
                val = val[:32] + "..." if len(val) > 35 else val
                print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} "
                      f"{Colors.BRIGHT_WHITE}{label}:{Colors.RESET} {Colors.BRIGHT_CYAN}{val:<35}{Colors.RESET}")
                info_count += 1
        if user_info.get('hireable'):
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} "
                  f"{Colors.BRIGHT_WHITE}Hireable:{Colors.RESET} {Colors.BRIGHT_GREEN}Yes{Colors.RESET}")
            info_count += 1
        if user_info.get('created_at'):
            created = datetime.strptime(user_info['created_at'][:10], "%Y-%m-%d")
            age = (datetime.now() - created).days
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} "
                  f"{Colors.BRIGHT_WHITE}Account Age:{Colors.RESET} {Colors.BRIGHT_CYAN}{age:,} days{Colors.RESET}")
            info_count += 1
        if info_count == 0:
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} "
                  f"{Colors.DIM}No additional information available{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
    
    def display_repository_statistics(self, repo_info: Dict):
        if not repo_info:
            self.print_error("No repository information available")
            return
        self.print_header("REPOSITORY ANALYTICS")
        print(f"{Colors.BRIGHT_GREEN}┌────────────────────────────────────────────────────────────┐{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.BRIGHT_MAGENTA}{Colors.BOLD}📦 REPOSITORY INFORMATION{Colors.RESET:<39}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}├────────────────────────────────────────────────────────────┤{Colors.RESET}")
        repo_display = f"{repo_info.get('owner','N/A')}/{repo_info.get('name','N/A')}"
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_CYAN}Repository:{Colors.RESET} {Colors.BRIGHT_WHITE}{repo_display:<48}{Colors.RESET}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        if repo_info.get('description'):
            desc = repo_info['description']
            desc = desc[:47] + "..." if len(desc) > 50 else desc
            print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_CYAN}Description:{Colors.RESET} {Colors.BRIGHT_YELLOW}{desc:<48}{Colors.RESET}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}└────────────────────────────────────────────────────────────┘{Colors.RESET}")
        print(f"\n{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}📊 REPOSITORY STATISTICS{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}\n")
        print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
        for label, key in [('⭐ Stars','stars'),('👁️ Watchers','watchers'),
                            ('🍴 Forks','forks'),('📂 Open Issues','open_issues'),
                            ('💾 Size (KB)','size')]:
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} "
                  f"{Colors.BRIGHT_MAGENTA}{label}:{Colors.RESET} "
                  f"{Colors.BRIGHT_WHITE}{repo_info.get(key,0):,}{Colors.RESET}")
        if repo_info.get('language'):
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} "
                  f"{Colors.BRIGHT_MAGENTA}💻 Main Language:{Colors.RESET} "
                  f"{Colors.BRIGHT_CYAN}{repo_info['language']}{Colors.RESET}")
        if repo_info.get('license'):
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} "
                  f"{Colors.BRIGHT_MAGENTA}📜 License:{Colors.RESET} "
                  f"{Colors.BRIGHT_WHITE}{repo_info['license']}{Colors.RESET}")
        if repo_info.get('archived'):
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} "
                  f"{Colors.BRIGHT_MAGENTA}📦 Status:{Colors.RESET} {Colors.BRIGHT_RED}Archived{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
        languages = repo_info.get('languages', {})
        if languages:
            total_bytes = sum(languages.values())
            print(f"\n{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}")
            print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}💻 LANGUAGE DISTRIBUTION{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}\n")
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
            for lang, bc in list(languages.items())[:5]:
                pct = bc / total_bytes * 100
                bar = '█' * int(pct/5) + '░' * (20 - int(pct/5))
                print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} "
                      f"{Colors.BRIGHT_CYAN}{lang:<15}{Colors.RESET} "
                      f"{Colors.BRIGHT_WHITE}{bar}{Colors.RESET} "
                      f"{Colors.BRIGHT_MAGENTA}{pct:.1f}%{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
        topics = repo_info.get('topics', [])
        if topics:
            print(f"\n{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}")
            print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}🏷️  TOPICS{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}\n")
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
            td = ", ".join(topics[:8])
            if len(topics) > 8:
                td += f" (+{len(topics)-8} more)"
            for line in self.wrap_text(td, 38):
                print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} {Colors.BRIGHT_CYAN}{line:<35}{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
        print(f"\n{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}📅 TIMELINE{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─'*60}{Colors.RESET}\n")
        print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
        for label, key in [('Created','created_at'),('Updated','updated_at'),('Last Push','pushed_at')]:
            if repo_info.get(key):
                dt = datetime.strptime(repo_info[key][:10], "%Y-%m-%d")
                days_ago = (datetime.now() - dt).days
                print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} "
                      f"{Colors.BRIGHT_WHITE}{label}:{Colors.RESET} "
                      f"{Colors.DIM}{dt.strftime('%Y-%m-%d')} ({days_ago} days ago){Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}{' '*10}{Colors.BRIGHT_WHITE}{'─'*40}{Colors.RESET}")
    
    def wrap_text(self, text: str, width: int) -> List[str]:
        words = text.split()
        lines, current_line, current_length = [], [], 0
        for word in words:
            if current_length + len(word) + len(current_line) <= width:
                current_line.append(word)
                current_length += len(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        if current_line:
            lines.append(' '.join(current_line))
        return lines
    
    def bulk_follow_users(self, usernames: List[str], delay: int = 10) -> Dict:
        results = {'successful': [], 'failed': [], 'total': len(usernames)}
        self.print_header("BULK FOLLOW OPERATION")
        print(f"{Colors.BRIGHT_CYAN}📋 Following {len(usernames)} users with {delay}s delay{Colors.RESET}\n")
        print(f"{Colors.BRIGHT_YELLOW}⚠️  Warning: Use responsibly!{Colors.RESET}\n")
        for i, username in enumerate(usernames, 1):
            print(f"\n{Colors.BRIGHT_CYAN}[{i}/{len(usernames)}]{Colors.RESET} Processing @{username}")
            success, message = self.follow_user(username)
            if success:
                self.print_success(f"Followed @{username}")
                results['successful'].append({'username': username, 'message': message})
            else:
                self.print_error(f"Failed @{username}: {message}")
                results['failed'].append({'username': username, 'message': message})
            if i < len(usernames):
                print(f"{Colors.DIM}Waiting {delay}s...{Colors.RESET}")
                for sec in range(delay, 0, -1):
                    sys.stdout.write(f"\r{Colors.DIM}Next follow in {sec}s...{Colors.RESET}")
                    sys.stdout.flush()
                    time.sleep(1)
                sys.stdout.write('\r' + ' ' * 30 + '\r')
        return results
    
    def bulk_star_repos(self, repos: List[Tuple[str, str]], delay: int = 15) -> Dict:
        results = {'successful': [], 'failed': [], 'total': len(repos)}
        self.print_header("BULK STAR OPERATION")
        print(f"{Colors.BRIGHT_CYAN}📋 Starring {len(repos)} repositories with {delay}s delay{Colors.RESET}\n")
        for i, (owner, repo) in enumerate(repos, 1):
            print(f"\n{Colors.BRIGHT_CYAN}[{i}/{len(repos)}]{Colors.RESET} Processing {owner}/{repo}")
            success, message = self.star_repository(owner, repo)
            if success:
                self.print_success(f"Starred {owner}/{repo}")
                results['successful'].append({'owner': owner, 'repo': repo, 'message': message})
            else:
                self.print_error(f"Failed {owner}/{repo}: {message}")
                results['failed'].append({'owner': owner, 'repo': repo, 'message': message})
            if i < len(repos):
                print(f"{Colors.DIM}Waiting {delay}s...{Colors.RESET}")
                for sec in range(delay, 0, -1):
                    sys.stdout.write(f"\r{Colors.DIM}Next star in {sec}s...{Colors.RESET}")
                    sys.stdout.flush()
                    time.sleep(1)
                sys.stdout.write('\r' + ' ' * 30 + '\r')
        return results
    
    def get_input(self, prompt: str, color: str = Colors.BRIGHT_CYAN,
                  password: bool = False) -> str:
        if password:
            import getpass
            return getpass.getpass(f"{color}{prompt}{Colors.BRIGHT_YELLOW}➜ {Colors.RESET}")
        return input(f"{color}{prompt}{Colors.BRIGHT_YELLOW}➜ {Colors.RESET}").strip()
    
    def handle_login_flow(self):
        print(f"\n{Colors.BRIGHT_CYAN}{'─'*50}{Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}✨ GitHub Login Options ✨{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─'*50}{Colors.RESET}\n")
        print(f"{Colors.BRIGHT_GREEN}[1]{Colors.RESET} {Colors.BRIGHT_WHITE}Login with Personal Access Token (Recommended){Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}[2]{Colors.RESET} {Colors.BRIGHT_WHITE}Login with Username/Password{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}[3]{Colors.RESET} {Colors.BRIGHT_WHITE}Back to main menu{Colors.RESET}")
        choice = self.get_input("\nSelect option (1-3)")
        if choice == '1':
            self.print_info("Get your token from: https://github.com/settings/developers")
            self.print_info("Required scopes: user, public_repo")
            token = self.get_input("Personal Access Token: ", Colors.BRIGHT_RED, password=True)
            if token:
                success, message = self.login_with_token(token)
                (self.print_success if success else self.print_error)(message)
        elif choice == '2':
            username = self.get_input("GitHub Username: ")
            password = self.get_input("Password: ", Colors.BRIGHT_RED, password=True)
            if username and password:
                success, message = self.login_with_credentials(username, password)
                (self.print_success if success else self.print_error)(message)
        elif choice == '3':
            return
        else:
            self.print_error("Invalid option! Please choose 1-3.")
    
    def handle_follow_flow(self):
        if not self.username or not self.access_token:
            self.print_error("Please login with access token first!")
            return
        self.print_header("FOLLOW MANAGEMENT")
        while True:
            print(f"\n{Colors.BRIGHT_CYAN}{'─'*50}{Colors.RESET}")
            print(f"{Colors.BRIGHT_MAGENTA}✨ Follow Options ✨{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}{'─'*50}{Colors.RESET}\n")
            print(f"{Colors.BRIGHT_GREEN}[1]{Colors.RESET} {Colors.BRIGHT_WHITE}Follow a single user{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}[2]{Colors.RESET} {Colors.BRIGHT_WHITE}Follow multiple users{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}[3]{Colors.RESET} {Colors.BRIGHT_WHITE}Unfollow a user{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}[4]{Colors.RESET} {Colors.BRIGHT_WHITE}Show followed users{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}[5]{Colors.RESET} {Colors.BRIGHT_WHITE}Back to main menu{Colors.RESET}")
            choice = self.get_input("\nSelect option (1-5)")
            if choice == '1':
                u = self.get_input("Enter username to follow (without @)")
                if u:
                    success, msg = self.follow_user(u)
                    (self.print_success if success else self.print_error)(msg)
            elif choice == '2':
                print(f"\n{Colors.BRIGHT_CYAN}{'─'*50}{Colors.RESET}")
                print(f"{Colors.DIM}• One username per line  • 'done' to finish  • 'clear' to reset{Colors.RESET}\n")
                usernames, count = [], 1
                while True:
                    ui = self.get_input(f"Username {count} (or 'done'): ").strip()
                    if ui.lower() == 'done':
                        if not usernames:
                            self.print_warning("No usernames entered!")
                            continue
                        break
                    elif ui.lower() == 'clear':
                        usernames, count = [], 1
                        self.print_success("List cleared!")
                    elif ui.lower() == 'list':
                        if usernames:
                            for i, n in enumerate(usernames, 1):
                                print(f"  {i}. @{n}")
                    elif not ui:
                        self.print_warning("Username cannot be empty!")
                    elif ui in usernames:
                        self.print_warning(f"@{ui} already in list!")
                    elif not self.verify_user_exists(ui):
                        self.print_warning(f"@{ui} doesn't seem to exist!")
                    else:
                        usernames.append(ui)
                        self.print_success(f"Added @{ui}")
                        count += 1
                if usernames:
                    delay = int(self.get_input("Delay between follows (seconds): ") or "15")
                    confirm = self.get_input(f"Follow {len(usernames)} users? (y/n): ").lower()
                    if confirm == 'y':
                        results = self.bulk_follow_users(usernames, delay)
                        print(f"\n✅ {len(results['successful'])}/{results['total']}  ❌ {len(results['failed'])}/{results['total']}")
            elif choice == '3':
                u = self.get_input("Enter username to unfollow (without @)")
                if u:
                    confirm = self.get_input(f"Unfollow @{u}? (y/n): ").lower()
                    if confirm == 'y':
                        success, msg = self.unfollow_user(u)
                        (self.print_success if success else self.print_error)(msg)
            elif choice == '4':
                if self.followed_users:
                    for i, user in enumerate(self.followed_users, 1):
                        print(f"  {i}. @{user['username']} - {Colors.DIM}{user['timestamp']}{Colors.RESET}")
                    print(f"\nTotal: {len(self.followed_users)}")
                else:
                    self.print_info("No users followed in this session yet.")
            elif choice == '5':
                break
            else:
                self.print_error("Invalid option! Please choose 1-5.")
            input(f"\n{Colors.BRIGHT_WHITE}Press Enter to continue...{Colors.RESET}")
            self.clear_screen()
            self.print_banner()
    
    def handle_repo_flow(self):
        if not self.username or not self.access_token:
            self.print_error("Please login with access token first!")
            return
        self.print_header("REPOSITORY OPERATIONS")
        while True:
            print(f"\n{Colors.BRIGHT_CYAN}{'─'*50}{Colors.RESET}")
            print(f"{Colors.BRIGHT_MAGENTA}✨ Repository Options ✨{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}{'─'*50}{Colors.RESET}\n")
            print(f"{Colors.BRIGHT_GREEN}[1]{Colors.RESET} {Colors.BRIGHT_WHITE}Get repository information{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}[2]{Colors.RESET} {Colors.BRIGHT_WHITE}Star a repository{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}[3]{Colors.RESET} {Colors.BRIGHT_WHITE}Star multiple repositories{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}[4]{Colors.RESET} {Colors.BRIGHT_WHITE}Fork a repository{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}[5]{Colors.RESET} {Colors.BRIGHT_WHITE}Back to main menu{Colors.RESET}")
            choice = self.get_input("\nSelect option (1-5)")
            if choice in ('1', '2', '4'):
                repo_input = self.get_input("Enter repository (owner/repo): ")
                if '/' not in repo_input:
                    self.print_error("Please use format: owner/repository")
                else:
                    owner, repo_name = (p.strip() for p in repo_input.split('/', 1))
                    if choice == '1':
                        info = self.get_repository_info(owner, repo_name)
                        if info:
                            self.display_repository_statistics(info)
                        else:
                            self.print_error("Failed to get repository information")
                    elif choice == '2':
                        success, msg = self.star_repository(owner, repo_name)
                        (self.print_success if success else self.print_error)(msg)
                    elif choice == '4':
                        success, msg = self.fork_repository(owner, repo_name)
                        (self.print_success if success else self.print_error)(msg)
            elif choice == '3':
                print(f"\n{Colors.BRIGHT_CYAN}{'─'*50}{Colors.RESET}")
                print(f"{Colors.DIM}• Format: owner/repo  • 'done' to finish  • 'clear' to reset{Colors.RESET}\n")
                repos, count = [], 1
                while True:
                    ui = self.get_input(f"Repository {count} (or 'done'): ").strip()
                    if ui.lower() == 'done':
                        if not repos:
                            self.print_warning("No repositories entered!")
                            continue
                        break
                    elif ui.lower() == 'clear':
                        repos, count = [], 1
                        self.print_success("Cleared!")
                    elif '/' not in ui:
                        self.print_warning("Please use format: owner/repository")
                    else:
                        o, r = (p.strip() for p in ui.split('/', 1))
                        if (o, r) in repos:
                            self.print_warning(f"{o}/{r} already in list!")
                        else:
                            repos.append((o, r))
                            self.print_success(f"Added {o}/{r}")
                            count += 1
                if repos:
                    delay = int(self.get_input("Delay between stars (seconds): ") or "20")
                    confirm = self.get_input(f"Star {len(repos)} repos? (y/n): ").lower()
                    if confirm == 'y':
                        results = self.bulk_star_repos(repos, delay)
                        print(f"\n✅ {len(results['successful'])}/{results['total']}  ❌ {len(results['failed'])}/{results['total']}")
            elif choice == '5':
                break
            else:
                self.print_error("Invalid option! Please choose 1-5.")
            input(f"\n{Colors.BRIGHT_WHITE}Press Enter to continue...{Colors.RESET}")
            self.clear_screen()
            self.print_banner()
    
    def handle_user_analysis_flow(self):
        self.print_header("USER ANALYSIS")
        while True:
            print(f"\n{Colors.BRIGHT_CYAN}{'─'*50}{Colors.RESET}")
            print(f"{Colors.BRIGHT_MAGENTA}✨ User Analysis Options ✨{Colors.RESET}")
            print(f"{Colors.BRIGHT_CYAN}{'─'*50}{Colors.RESET}\n")
            print(f"{Colors.BRIGHT_GREEN}[1]{Colors.RESET} {Colors.BRIGHT_WHITE}Analyze your own account{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}[2]{Colors.RESET} {Colors.BRIGHT_WHITE}Analyze another user{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}[3]{Colors.RESET} {Colors.BRIGHT_WHITE}Back to main menu{Colors.RESET}")
            choice = self.get_input("\nSelect option (1-3)")
            if choice == '1':
                if self.username:
                    info = self.get_user_info(self.username)
                    if info:
                        self.display_user_statistics(info)
                    else:
                        self.print_error("Failed to get your user information")
                else:
                    self.print_error("Please login first!")
            elif choice == '2':
                u = self.get_input("Enter username to analyze (without @): ")
                if u:
                    if self.verify_user_exists(u):
                        info = self.get_user_info(u)
                        if info:
                            self.display_user_statistics(info)
                        else:
                            self.print_error("Failed to get user information")
                    else:
                        self.print_error(f"User @{u} not found")
            elif choice == '3':
                break
            else:
                self.print_error("Invalid option! Please choose 1-3.")
            input(f"\n{Colors.BRIGHT_WHITE}Press Enter to continue...{Colors.RESET}")
            self.clear_screen()
            self.print_banner()
    
    def print_menu(self):
        self.print_header("GITHUB TOOL - MAIN MENU")
        logged_in = (f"{Colors.BRIGHT_GREEN}✅ @{self.username}{Colors.RESET}"
                     if self.username else f"{Colors.BRIGHT_RED}❌ Not logged in{Colors.RESET}")
        token_st  = (f"{Colors.BRIGHT_GREEN}✅ Token active{Colors.RESET}"
                     if self.access_token else f"{Colors.BRIGHT_RED}❌ No token{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}┌────────────────────────────────────────────────────────────┐{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.BRIGHT_CYAN}                     Available Options                      {Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}├────────────────────────────────────────────────────────────┤{Colors.RESET}")
        for n, label in [('1','Login to GitHub Account'),('2','User Profile Analysis'),
                          ('3','Follow/Unfollow Users'),('4','Repository Operations'),
                          ('5','Followback Checker & Cleaner'),('6','Seed User Follower Extractor'),
                          ('7','Check Rate Limits'),('8','Exit Tool')]:
            print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_YELLOW}{n}.{Colors.RESET} {Colors.BRIGHT_WHITE}{label:<52}{Colors.RESET}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}├────────────────────────────────────────────────────────────┤{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_CYAN}Status:{Colors.RESET} {logged_in:<48}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}│{Colors.RESET} {Colors.BRIGHT_CYAN}Token:{Colors.RESET}  {token_st:<48}{Colors.BRIGHT_GREEN}{Colors.RESET}")
        print(f"{Colors.BRIGHT_GREEN}└────────────────────────────────────────────────────────────┘{Colors.RESET}\n")
    
    def check_rate_limits(self):
        try:
            self.print_header("API RATE LIMITS")
            response = self.session.get(f"{self.api_url}/rate_limit")
            if response.status_code == 200:
                rd = response.json()
                for name, key, icon in [('Core API','core','📊'),
                                         ('Search API','search','🔍'),
                                         ('GraphQL API','graphql','📈')]:
                    if key not in rd['resources']:
                        continue
                    r = rd['resources'][key]
                    reset = datetime.fromtimestamp(r['reset']).strftime('%Y-%m-%d %H:%M:%S')
                    used_pct = (r['limit'] - r['remaining']) / r['limit'] * 100
                    print(f"\n{Colors.BRIGHT_CYAN}{icon} {name}:{Colors.RESET}")
                    print(f"  Remaining: {r['remaining']}/{r['limit']} ({used_pct:.1f}% used)")
                    print(f"  Resets at: {reset}")
                if rd['resources']['core']['remaining'] < 100:
                    self.print_warning("Core API limit is low!")
                if rd['resources']['search']['remaining'] < 10:
                    self.print_warning("Search API limit is very low!")
            else:
                self.print_error("Failed to get rate limit information")
        except Exception as e:
            self.print_error(f"Error checking rate limits: {e}")
    
    def run(self):
        self.clear_screen()
        self.print_banner()
        while True:
            self.print_menu()
            choice = self.get_input("Select an option (1-8)")
            handlers = {
                '1': self.handle_login_flow,
                '2': self.handle_user_analysis_flow,
                '3': self.handle_follow_flow,
                '4': self.handle_repo_flow,
                '5': self.handle_followback_cleaner_flow,
                '6': self.handle_seed_follower_extractor_flow,
                '7': self.check_rate_limits,
            }
            if choice in handlers:
                self.clear_screen()
                self.print_banner()
                handlers[choice]()
            elif choice == '8':
                self.clear_screen()
                self.print_banner()
                if self.followed_users or self.starred_repos:
                    print(f"\n{Colors.BRIGHT_CYAN}{'═'*60}{Colors.RESET}")
                    print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}✨ Session Summary ✨{Colors.RESET}")
                    print(f"{Colors.BRIGHT_CYAN}{'═'*60}{Colors.RESET}\n")
                    if self.followed_users:
                        print(f"{Colors.BRIGHT_GREEN}📊 Followed this session: {len(self.followed_users)}{Colors.RESET}")
                    if self.starred_repos:
                        print(f"{Colors.BRIGHT_BLUE}⭐ Starred this session: {len(self.starred_repos)}{Colors.RESET}")
                self.print_success("Thank you for using GitHub Tool! 👋")
                print(f"\n{Colors.DIM}Session duration: "
                      f"{(datetime.now()-self.session_start_time).seconds}s{Colors.RESET}\n")
                break
            else:
                self.print_error("Invalid option! Please choose 1-8.")
            input(f"\n{Colors.BRIGHT_WHITE}Press Enter to continue...{Colors.RESET}")
            self.clear_screen()
            self.print_banner()


def main():
    try:
        GitHubTool().run()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.BRIGHT_YELLOW}👋 Goodbye! Thanks for using GitHub Tool!{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.BRIGHT_RED}💥 An unexpected error occurred: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
