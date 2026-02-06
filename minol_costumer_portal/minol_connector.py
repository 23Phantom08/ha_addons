"""
Minol Customer Portal API Client

Handles authentication and data fetching from the Minol customer portal
using Playwright for Azure B2C SAML authentication and requests for API calls.
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
import base64
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
}


class MinolConnector:
    """Minol customer portal API client with Playwright-based authentication."""

    def __init__(self, email: str, password: str, base_url: str = "https://webservices.minol.com"):
        """Initialize the connector with user credentials."""
        self.email = email
        self.password = password

        self.base_url = base_url
        self.login_url = f"{base_url}/"
        self.acs_url = f"{base_url}/saml2/sp/acs"

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        })

        self.user_tenants = None
        self.user_num = None
        self.user_info = {}
        self.csrf_token = None
        self._authenticated = False
        self._last_data: Optional[Dict] = None
        self._last_update: Optional[datetime] = None
        self._cache_duration = timedelta(hours=1)

    def login(self):
        """Perform Azure B2C SAML authentication using Playwright."""
        logger.info("Starting Playwright authentication...")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = browser.new_context()
            page = context.new_page()

            try:
                logger.info("Navigating to monitoring page...")
                monitoring_url = f"{self.base_url}/minol.com~kundenportal~em~web/resources/monitoring/index.html?isMieter=true&redirect2=true"
                page.goto(monitoring_url, wait_until="networkidle", timeout=90000)

                time.sleep(3)
                logger.info(f"Current URL: {page.url}")

                if "minolauth.b2clogin.com" in page.url:
                    logger.info("On Azure B2C login page")
                else:
                    logger.info("Checking for login redirect...")
                    page_content = page.content()
                    with open("current_page.html", "w", encoding="utf-8") as f:
                        f.write(page_content)

                    try:
                        page.wait_for_url("**/minolauth.b2clogin.com/**", timeout=5000)
                    except Exception:
                        logger.warning("No redirect to Azure B2C detected")

                if "minolauth.b2clogin.com" in page.url:
                    logger.info("Filling login form...")
                    time.sleep(2)

                    email_input = page.locator('input[id="signInName"], input[name="signInName"], input[type="email"], input[placeholder*="Kundennummer"]')
                    email_input.wait_for(state="visible", timeout=10000)
                    email_input.fill(self.email)

                    password_input = page.locator('input[id="password"], input[name="password"], input[type="password"]')
                    password_input.wait_for(state="visible", timeout=5000)
                    password_input.fill(self.password)

                    sign_in_button = page.locator('button[type="submit"], button#next')
                    sign_in_button.click()

                    logger.info("Waiting for redirect...")
                    page.wait_for_url(f"{self.base_url}/**", timeout=30000)
                    time.sleep(2)

                    logger.info("Navigating to monitoring page...")
                    page.goto(monitoring_url, wait_until="networkidle")
                    time.sleep(3)
                else:
                    logger.info("Checking authentication status...")

                logger.info("Extracting cookies...")
                cookies = context.cookies()

                for cookie in cookies:
                    self.session.cookies.set(
                        name=cookie['name'],
                        value=cookie['value'],
                        domain=cookie.get('domain', ''),
                        path=cookie.get('path', '/'),
                        secure=cookie.get('secure', False)
                    )

                logger.info(f"Transferred {len(cookies)} cookies")

                mysapsso2_present = any(c['name'] == 'MYSAPSSO2' for c in cookies)
                if mysapsso2_present:
                    logger.info("MYSAPSSO2 cookie obtained")
                else:
                    logger.warning("MYSAPSSO2 cookie not found")

            except Exception as e:
                logger.error(f"Error during Playwright login: {e}")
                raise
            finally:
                browser.close()

        logger.info("Login successful.")
        self._authenticated = True


    def _get_monitoring_index(self):
        """Access the monitoring index page."""
        logger.info("Getting monitoring index page...")
        url = f"{self.base_url}/minol.com~kundenportal~em~web/resources/monitoring/index.html?isMieter=true"
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'de-DE,de;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
            'DNT': '1',
            'Referer': f'{self.base_url}/minol.com~kundenportal~em~web/resources/monitoring/index.html?isMieter=true/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        }
        try:
            response = self.session.get(url, headers=headers, allow_redirects=True)
            response.raise_for_status()
            with open("monitoring_index_page.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.info(f"Monitoring index page response status code: {response.status_code}")
            logger.info(f"Monitoring index page response cookies: {response.cookies}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting monitoring index page: {e}")
            raise
    
    def _get_monitoring_client(self):
        """Complete the login process by accessing the monitoring client URL."""
        logger.info("Getting monitoring client...")
        url = f"{self.base_url}/irj/servlet/prt/portal/prtroot/pcd!3aportal_content!2fminol!2ff_PortalLayouts!2fv_monitoringClient"
        try:
            response = self.session.get(url, allow_redirects=True)
            response.raise_for_status()
            with open("monitoring_page_response.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.info(f"Monitoring client response status code: {response.status_code}")
            logger.info(f"Monitoring client response cookies: {response.cookies}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting monitoring client: {e}")
            raise

    def get_user_tenants(self):
        """Fetch user tenants to extract the userNum and profile data."""
        logger.info("Fetching user tenants...")
        url = f"{self.base_url}/minol.com~kundenportal~em~web/rest/EMData/getUserTenants"
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/json; charset=utf-8',
            'Referer': f'{self.base_url}/minol.com~kundenportal~em~web/resources/monitoring/index.html?isMieter=true',
            'X-Requested-With': 'XMLHttpRequest'
        }
        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()

            self.user_tenants = response.json()
            
            if self.user_tenants and len(self.user_tenants) > 0:
                # Hier ziehen wir die Daten für das Profil (Index 0)
                tenant_data = self.user_tenants[0]
                
                # 1. Einzelvariablen setzen
                self.user_num = tenant_data.get("userNumber")
                self.lgnr = tenant_data.get("lgnr")
                self.full_name = tenant_data.get("name")
                
                # 2. WICHTIG: Das user_info Dictionary befüllen (das nutzt die main.py!)
                self.user_info = {
                    "userNumber": tenant_data.get("userNumber"),
                    "lgnr": tenant_data.get("lgnr"),
                    "name": tenant_data.get("name"),
                    "email": tenant_data.get("email"),
                    "addrCity": tenant_data.get("addrCity"),
                    "addrStreet": tenant_data.get("addrStreet"),
                    "addrHouseNum": tenant_data.get("addrHouseNum"),
                    "addrPostalCode": tenant_data.get("addrPostalCode"),
                    "geschossText": tenant_data.get("geschossText"),
                    "lageText": tenant_data.get("lageText"),
                    "einzugMieter": tenant_data.get("einzugMieter"),
                    "nenr": tenant_data.get("nenr", "000003") # Fallback falls leer
                }

                logger.info(f"userNum found: {self.user_num} for {self.full_name}")
            else:
                raise ValueError("User tenants not found or empty.")
        except Exception as e:
            logger.error(f"Error fetching user tenants: {e}")
            raise

    def fetch_em_data(self, timeline_start, timeline_end, cons_type="HZKWH", dlg_key="100KWH"):
        """
        Fetch eMonitoring data for a specific consumption type.

        Args:
            timeline_start (str): Start period in format YYYYMM (e.g., "202411")
            timeline_end (str): End period in format YYYYMM (e.g., "202510")
            cons_type (str): Type of consumption - "HZKWH", "WARMWASSER", or "KALTWASSER"
            dlg_key (str): Dialog key, default "100KWH" for heating

        Returns:
            dict: JSON response containing table (per room) and chart (timeline) data
        """
        logger.info(f"Fetching eMonitoring data for {cons_type} from {timeline_start} to {timeline_end}")
        url = f"{self.base_url}/minol.com~kundenportal~em~web/rest/EMData/readData"
        payload = {
            "userNum": self.user_num,
            "layer": "NE",
            "scale": "CALMONTH",
            "chartRefUnit": "ABS",
            "refObject": "DIN_AVG",
            "consType": cons_type,
            "dashBoardKey": "PE",
            "timelineStart": timeline_start,
            "timelineStartTxt": f"{timeline_start[4:]}.{timeline_start[:4]}",
            "timelineEnd": timeline_end,
            "timelineEndTxt": f"{timeline_end[4:]}.{timeline_end[:4]}",
            "valuesInKWH": True,
            "dlgKey": dlg_key,
        }
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json; charset=UTF-8",
            "Referer": f'{self.base_url}/minol.com~kundenportal~em~web/resources/monitoring/index.html?isMieter=true',
            "X-Requested-With": "XMLHttpRequest",
        }

        logger.debug(f"Fetching EM data from URL: {url}")
        logger.debug(f"Request Payload: {json.dumps(payload, indent=2)}")
        logger.debug(f"Request Headers: {json.dumps(headers, indent=2)}")

        try:
            response = self.session.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            logger.debug(f"EM data response status: {response.status_code}")
            logger.debug(f"EM data response content: {response.text[:200]}...")
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching EM data: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding EM data response: {e}")
            with open("em_data_error_response.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.error("Response content saved to em_data_error_response.html")
            raise

    def get_all_consumption_data(self, timeline_start, timeline_end):
        """
        Fetch all consumption data types (heating, hot water, cold water) organized by room.

        Args:
            timeline_start (str): Start period in format YYYYMM (e.g., "202411")
            timeline_end (str): End period in format YYYYMM (e.g., "202510")

        Returns:
            dict: Structured consumption data with the following format:
                {
                    "heating": {
                        "by_room": [list of room consumption data],
                        "timeline": [list of monthly data],
                        "total_consumption": float
                    },
                    "hot_water": {
                        "by_room": [list of room consumption data],
                        "timeline": [list of monthly data],
                        "total_consumption": float
                    },
                    "cold_water": {
                        "by_room": [list of room consumption data],
                        "timeline": [list of monthly data],
                        "total_consumption": float
                    },
                    "timestamp": "ISO timestamp",
                    "period": {"start": "YYYYMM", "end": "YYYYMM"}
                }
        """
        from datetime import datetime

        logger.info(f"Fetching all consumption data from {timeline_start} to {timeline_end}")

        consumption_data = {
            "timestamp": datetime.now().isoformat(),
            "period": {
                "start": timeline_start,
                "end": timeline_end
            }
        }

        try:
            heating_raw = self.fetch_em_data(timeline_start, timeline_end, cons_type="HZKWH", dlg_key="100KWH")
            consumption_data["heating"] = self._process_consumption_data(
                heating_raw, "HEIZUNG", timeline_start, timeline_end
            )
        except Exception as e:
            logger.error(f"Error fetching heating data: {e}")
            consumption_data["heating"] = {"error": str(e)}

        try:
            hot_water_raw = self.fetch_em_data(timeline_start, timeline_end, cons_type="WARMWASSER", dlg_key="100WW")
            consumption_data["hot_water"] = self._process_consumption_data(
                hot_water_raw, "WARMWASSER", timeline_start, timeline_end
            )
        except Exception as e:
            logger.error(f"Error fetching hot water data: {e}")
            consumption_data["hot_water"] = {"error": str(e)}

        try:
            cold_water_raw = self.fetch_em_data(timeline_start, timeline_end, cons_type="KALTWASSER", dlg_key="100KW")
            consumption_data["cold_water"] = self._process_consumption_data(
                cold_water_raw, "KALTWASSER", timeline_start, timeline_end
            )
        except Exception as e:
            logger.error(f"Error fetching cold water data: {e}")
            consumption_data["cold_water"] = {"error": str(e)}

        return consumption_data

    def _process_consumption_data(self, raw_data, consumption_type, timeline_start, timeline_end):
        """
        Process raw consumption data into a structured format.

        Note: The Minol API currently only provides timeline data on aggregate level,
        not per individual room/device. Room timeline data is not available from the API.

        Args:
            raw_data (dict): Raw API response
            consumption_type (str): Type identifier (HEIZUNG, WARMWASSER, KALTWASSER)
            timeline_start (str): Start period (for documentation)
            timeline_end (str): End period (for documentation)

        Returns:
            dict: Processed data with by_room, overall timeline, and total_consumption
        """
        processed = {
            "by_room": [],
            "timeline": [],
            "total_consumption": 0.0
        }

        if "table" in raw_data and raw_data["table"]:
            for room_data in raw_data["table"]:
                room_info = {
                    "room_name": room_data.get("raum", "Unknown"),
                    "room_key": room_data.get("raumKey"),
                    "device_number": room_data.get("gerNr"),
                    "consumption": room_data.get("consumption", 0),
                    "unit": room_data.get("unit", "KWH"),
                    "consumption_evaluated": room_data.get("consumptionBew", 0),
                    "evaluation_score": room_data.get("bewertung"),
                    "reading": room_data.get("ablesung", 0),
                    "initial_reading": room_data.get("anfangsstand", 0),
                    # Note: Per-room timeline not available from API
                }
                processed["by_room"].append(room_info)
                processed["total_consumption"] += room_data.get("consumption", 0)

        if "chart" in raw_data and raw_data["chart"]:
            for entry in raw_data["chart"]:
                if entry.get("keyFigure") != "REF":
                    timeline_entry = {
                        "period": entry.get("category"),
                        "period_int": entry.get("categoryInt"),
                        "value": entry.get("value", 0),
                        "label": entry.get("label"),
                        "num_values": entry.get("anzValues", 0)
                    }
                    processed["timeline"].append(timeline_entry)

        return processed

    def authenticate(self) -> bool:
        """
        Authenticate with the Minol portal.

        This is a convenience wrapper around login() + get_user_tenants().

        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            logger.info("Authenticating with Minol portal...")
            self.login()
            self.get_user_tenants()
            logger.info("Authentication successful")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self._authenticated = False
            return False

    def get_consumption_data(self, months_back: int = 12, force_update: bool = False) -> Optional[Dict]:
        # Cache prüfen
        if not force_update and self._last_data and self._last_update:
            if datetime.now() - self._last_update < self._cache_duration:
                return self._last_data

        # Authentifizierung
        if not self._authenticated:
            if not self.authenticate():
                return None

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30 * months_back)

            timeline_start = start_date.strftime("%Y%m")
            timeline_end = end_date.strftime("%Y%m")

            logger.info(
                f"Fetching consumption data from {timeline_start} to {timeline_end}"
            )

            # Alle Verbrauchsdaten abrufen
            data = self.get_all_consumption_data(
                timeline_start=timeline_start,
                timeline_end=timeline_end
            )

            if not data:
                logger.error("No consumption data received from Minol API")
                return None

            # Cache aktualisieren
            self._last_data = data
            self._last_update = datetime.now()
            return data

        except Exception as e:
            logger.error(f"Error fetching consumption data: {e}", exc_info=True)
            return None



