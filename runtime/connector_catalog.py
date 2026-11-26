"""AIBO connector discovery and setup-request catalog.

Names are discovery candidates, NOT claims of implemented adapters or authenticated
connections. No credentials or customer content stored. Existing runtime/connectors.json
remains unchanged and is the only source for currently registered HTTP adapters.
"""
import json
import os
import sys
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
STATE = Path(os.environ.get('AIBO_STATE_DIR', str(Path.home()/'.aibo-state')))
_LOCK = threading.RLock()

# Category label and vendor names. Include the integrations most often requested by
# SMBs and teams, including publishing, analytics, code hosting, and AI media.
GROUPS = {
    'Social media & communities': [
        'Instagram', 'Facebook Pages', 'Facebook Groups', 'Threads', 'TikTok',
        'YouTube', 'YouTube Analytics', 'LinkedIn Pages', 'LinkedIn Profiles',
        'Pinterest', 'Pinterest Ads', 'Pinterest Analytics', 'X (Twitter)', 'Bluesky', 'Reddit', 'Mastodon', 'Discord', 'Telegram', 'WhatsApp Business'],
    'Scheduling & publishing': [
        'Buffer', 'Hootsuite', 'Later', 'Metricool', 'Publer', 'Sprout Social',
        'Planable', 'SocialBee', 'Loomly', 'Agorapulse', 'Meta Business Suite',
        'Calendly', 'Cal.com', 'Google Calendar', 'Microsoft Outlook Calendar', 'Acuity Scheduling', 'TidyCal'],
    'Graphic design & assets': [
        'Canva', 'Adobe Express', 'Adobe Creative Cloud', 'Figma', 'Framer',
        'Photopea', 'Cloudinary', 'Unsplash', 'Pexels', 'Google Photos'],
    'Video, audio & AI media': [
        'HeyGen', 'VEED', 'Visla', 'Runway', 'Descript', 'Synthesia',
        'CapCut', 'ElevenLabs', 'Vimeo', 'Loom', 'Wistia', 'Mux', 'Cloudflare Stream',
        'OpenAI Images', 'Sora'],
    'Websites, hosting & deployments': [
        'Vercel', 'Netlify', 'Cloudflare Pages', 'Cloudflare DNS', 'Firebase Hosting',
        'GitHub Pages', 'AWS', 'Google Cloud', 'Azure', 'DigitalOcean',
        'Webflow', 'WordPress', 'Wix', 'Squarespace', 'Shopify', 'HostEurope'],
    'Databases, auth & backend': [
        'Supabase', 'Firebase', 'Firestore', 'Firebase Authentication', 'Firebase Storage',
        'Neon', 'PlanetScale', 'MongoDB Atlas', 'Airtable', 'PostgreSQL', 'Redis Cloud', 'Appwrite'],
    'Email & customer messaging': [
        'Gmail', 'Microsoft Outlook Email', 'Resend', 'SendGrid', 'Mailgun',
        'Amazon SES', 'Postmark', 'Brevo', 'Mailchimp', 'Klaviyo',
        'Customer.io', 'Twilio', 'Intercom', 'Zendesk', 'Freshdesk'],
    'CRM, sales & payments': [
        'HubSpot', 'Pipedrive', 'Salesforce', 'Zoho CRM', 'Attio', 'Close CRM',
        'Stripe', 'PayPal', 'Square', 'Paddle', 'QuickBooks', 'Xero', 'MYOB'],
    'Files, documents & collaboration': [
        'Google Drive', 'Google Docs', 'Google Sheets', 'Google Slides',
        'Microsoft OneDrive', 'Microsoft SharePoint', 'Microsoft Excel',
        'Notion', 'Slack', 'Microsoft Teams', 'Dropbox', 'Box', 'Asana',
        'Trello', 'ClickUp', 'Linear', 'Jira'],
    'Analytics, search & advertising': [
        'Google Analytics 4', 'Google Search Console', 'Google Ads',
        'Meta Ads', 'TikTok Ads', 'LinkedIn Ads', 'Microsoft Advertising',
        'Google Tag Manager', 'Looker Studio', 'Mixpanel', 'PostHog',
        'Plausible', 'Matomo', 'Semrush', 'Ubersuggest', 'Ahrefs'],
    'Developer tools & automation': [
        'GitHub', 'GitLab', 'Bitbucket', 'Sentry', 'Datadog',
        'Zapier', 'Make', 'n8n', 'Pabbly Connect', 'IFTTT', 'MCP servers'],
    'Commerce storefronts & marketplaces': [
        'WooCommerce', 'BigCommerce', 'Etsy', 'Amazon Seller Central',
        'eBay Seller Hub', 'Walmart Marketplace', 'TikTok Shop', 'Shopify POS',
        'Shopify Markets', 'Shopware', 'Ecwid', 'PrestaShop', 'Magento / Adobe Commerce',
        'Square Online', 'Faire Wholesale'],
    'Print-on-demand & fulfillment': [
        'Printful', 'Printify', 'Gelato Print', 'Gelato API', 'Gooten', 'Prodigi',
        'SPOD', 'Apliiq', 'CustomCat', 'TeeLaunch', 'T-Pop', 'Lulu Direct',
        'Bookvault', 'IngramSpark', 'Print Aura', 'JetPrint', 'Contrado',
        'ShineOn', 'Printrove'],
    'Dropshipping & supplier sourcing': [
        'DSers', 'AliExpress', 'CJdropshipping', 'Spocket', 'Zendrop',
        'AutoDS', 'Syncee', 'SaleHoo', 'Modalyst', 'Wholesale2B',
        'Inventory Source', 'AppScenic', 'BigBuy', 'BrandsGateway',
        'Doba', 'Dropified', 'HyperSKU', 'EPROLO', 'Trendsi', 'Zopi',
        'Wiio', 'Temu Seller Center'],
    'Shipping, inventory & orders': [
        'ShipStation', 'Shippo', 'Easyship', 'Sendcloud', 'AfterShip',
        'ShipBob', 'Flexport', 'DHL Business', 'UPS', 'FedEx', 'Royal Mail',
        'Amazon FBA', 'Cin7', 'Katana MRP', 'Linnworks', 'Order Desk'],
    'Book publishing & distribution': [
        'Amazon Kindle Direct Publishing (KDP)', 'KDP Print', 'KDP Select',
        'Apple Books for Authors', 'Kobo Writing Life', 'Google Play Books Partner Center',
        'Draft2Digital', 'Smashwords', 'StreetLib', 'PublishDrive',
        'Barnes & Noble Press', 'Lulu Publishing', 'Blurb', 'BookBaby',
        'Reedsy', 'Atticus', 'Vellum', 'Kindle Create', 'Adobe InDesign',
        'BookFunnel', 'StoryOrigin', 'ACX', 'Findaway Voices',
        'Spotify for Authors', 'Author’s Republic', 'InAudio'],
    'Book marketing & advertising': [
        'Amazon Ads for Books', 'BookBub Ads', 'BookBub Featured Deals',
        'Goodreads Author Program', 'Goodreads Giveaways',
        'Freebooksy', 'Bargain Booksy', 'Written Word Media', 'Fussy Librarian',
        'BookSirens', 'NetGalley', 'Booksprout', 'BooksGoSocial',
        'StoryGraph', 'LibraryThing', 'BookBrush', 'Publisher Rocket',
        'KDSpy', 'BookReport', 'ReaderLinks', 'BookFunnel Promotions'],
    'Planners, printables & digital products': [
        'Gumroad', 'Payhip', 'Sellfy', 'Creative Market', 'Design Bundles',
        'Creative Fabrica', 'Teachers Pay Teachers', 'Ko-fi Shop',
        'Stan Store', 'Fourthwall', 'Lemon Squeezy', 'Podia',
        'Notion Marketplace', 'Goodnotes Marketplace', 'Zinnia',
        'Canva Templates', 'Corjl', 'Templett', 'JetTemplate',
        'Affinity Publisher', 'Affinity Designer', 'Scribus',
        'Kittl', 'Book Bolt', 'Tangent Templates'],
    'Lockscreens, wallpapers & visual distribution': [
        'Zedge', 'Walli', 'Wallpaper Engine Workshop', 'Etsy Digital Wallpapers',
        'Pinterest Organic', 'Pinterest Business', 'Instagram Shops',
        'TikTok Business', 'Behance', 'Dribbble', 'DeviantArt',
        'ArtStation Marketplace', 'Redbubble', 'Society6', 'Displate',
        'ArtStation', 'Creative Cloud Libraries'],
    'Language, translation & localization': [
        'DeepL API', 'Google Cloud Translation', 'Microsoft Azure AI Translator',
        'Amazon Translate', 'Lokalise', 'Crowdin', 'Phrase Localization',
        'Smartling', 'Transifex', 'Weblate', 'Weglot', 'WPML', 'Polylang',
        'TranslatePress', 'Tolgee', 'POEditor', 'Locize', 'i18next',
        'FormatJS', 'Lingui', 'Paraglide JS', 'Lingo.dev', 'XTM Cloud',
        'memoQ', 'Trados', 'GlobalLink', 'RWS Language Weaver',
        'Localazy', 'SimpleLocalize', 'Prismic Localization', 'Contentful Localization',
        'Sanity Localization', 'Next.js internationalization',
        'hreflang & multilingual SEO', 'Multilingual accessibility QA'],
    'Browser & web workflows': [
        'Playwright', 'Chromium', 'Google Chrome', 'Microsoft Edge',
        'Firefox', 'Selenium', 'Browserbase', 'Browserless', 'Chrome DevTools',
        'Puppeteer', 'Chrome Remote Debugging', 'Microsoft Edge WebDriver',
        'Firefox WebDriver', 'Playwright MCP', 'Browser Use', 'Stagehand'],
}

# Explicit mapping between published provider names and IDs in the existing
# runtime/connectors.json. Do not infer operational readiness from registration.
REGISTERED_IDS = {
    'github': 'GitHub', 'hubspot': 'HubSpot', 'pipedrive': 'Pipedrive',
    'supabase': 'Supabase', 'vercel': 'Vercel', 'stripe': 'Stripe',
    'google-calendar': 'Google Calendar',
}

def _id(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

def entries():
    registry = ROOT / 'runtime' / 'connectors.json'
    try:
        raw = json.loads(registry.read_text(encoding='utf8'))
        registered = {v.get('id') for v in raw.get('connectors', [])}
    except (FileNotFoundError, json.JSONDecodeError, AttributeError, TypeError):
        registered = set()
    reverse = {v: k for k, v in REGISTERED_IDS.items()}
    result = []
    ids = set()
    for category, names in GROUPS.items():
        for name in names:
            cid = _id(name)
            if cid in ids:
                continue
            ids.add(cid)
            reg = reverse.get(name)
            result.append({'id': cid, 'name': name, 'category': category,
                           'status': 'runtime-registered' if reg in registered else 'catalog-only',
                           'registryId': reg if reg in registered else None,
                           'connected': False})
    return result

def requests_path():
    return STATE / 'connection-requests.json'

def requests():
    p = requests_path()
    try:
        data = json.loads(p.read_text(encoding='utf8'))
        return data if isinstance(data, list) else []
    except (FileNotFoundError, ValueError):
        return []

def catalog():
    items = entries()
    return {'connectors': items, 'total': len(items),
            'registered': sum(x['status'] == 'runtime-registered' for x in items),
            'connected': 0, 'requests': requests(),
            'notice': 'Catalog listings are not live connectors. Registry entries are not authenticated connections.'}

def request_connection(data):
    try:
        from .products import ProductError, project_records
    except ImportError:
        from products import ProductError, project_records
    if not isinstance(data, dict):
        raise ProductError('Invalid request')
    connector = data.get('connector')
    project = data.get('project')
    if not isinstance(connector, str) or connector not in {x['id'] for x in entries()}:
        raise ProductError('Unknown connector')
    if not isinstance(project, str) or project not in {x['id'] for x in project_records()}:
        raise ProductError('Choose an existing project')
    with _LOCK:
        current = requests()
        for existing in current:
            if existing['connector'] == connector and existing['project'] == project and existing['status'] == 'setup-requested':
                return {'ok': True, 'request': existing, 'alreadyRequested': True}
        item = {'id': os.urandom(12).hex(), 'connector': connector, 'project': project,
                'status': 'setup-requested', 'createdAt': datetime.now(timezone.utc).isoformat()}
        current.append(item)
        p = requests_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.connection-', dir=p.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf8') as fp:
                json.dump(current, fp, indent=2)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(tmp, p)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return {'ok': True, 'request': item, 'alreadyRequested': False}
