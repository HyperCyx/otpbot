from db import get_country_capacities, get_user
from utils import require_channel_membership
from bot_init import bot
from translations import get_text

# Import withdrawal state to check for active withdrawals
from withdraw import user_withdraw_state, clear_withdraw_state

COUNTRY_INFO = {
    "+93": {"name": "Afghanistan", "flag": "🇦🇫"},
    "+355": {"name": "Albania", "flag": "🇦🇱"},
    "+213": {"name": "Algeria", "flag": "🇩🇿"},
    "+376": {"name": "Andorra", "flag": "🇦🇩"},
    "+244": {"name": "Angola", "flag": "🇦🇴"},
    "+1-268": {"name": "Antigua and Barbuda", "flag": "🇦🇬"},
    "+54": {"name": "Argentina", "flag": "🇦🇷"},
    "+374": {"name": "Armenia", "flag": "🇦🇲"},
    "+61": {"name": "Australia", "flag": "🇦🇺"},
    "+43": {"name": "Austria", "flag": "🇦🇹"},
    "+994": {"name": "Azerbaijan", "flag": "🇦🇿"},
    "+1-242": {"name": "Bahamas", "flag": "🇧🇸"},
    "+973": {"name": "Bahrain", "flag": "🇧🇭"},
    "+880": {"name": "Bangladesh", "flag": "🇧🇩"},
    "+1-246": {"name": "Barbados", "flag": "🇧🇧"},
    "+375": {"name": "Belarus", "flag": "🇧🇾"},
    "+32": {"name": "Belgium", "flag": "🇧🇪"},
    "+501": {"name": "Belize", "flag": "🇧🇿"},
    "+229": {"name": "Benin", "flag": "🇧🇯"},
    "+975": {"name": "Bhutan", "flag": "🇧🇹"},
    "+591": {"name": "Bolivia", "flag": "🇧🇴"},
    "+387": {"name": "Bosnia and Herzegovina", "flag": "🇧🇦"},
    "+267": {"name": "Botswana", "flag": "🇧🇼"},
    "+55": {"name": "Brazil", "flag": "🇧🇷"},
    "+673": {"name": "Brunei", "flag": "🇧🇳"},
    "+359": {"name": "Bulgaria", "flag": "🇧🇬"},
    "+226": {"name": "Burkina Faso", "flag": "🇧🇫"},
    "+257": {"name": "Burundi", "flag": "🇧🇮"},
    "+855": {"name": "Cambodia", "flag": "🇰🇭"},
    "+237": {"name": "Cameroon", "flag": "🇨🇲"},
    "+1": {"name": "Canada", "flag": "🇨🇦"},
    "+238": {"name": "Cape Verde", "flag": "🇨🇻"},
    "+236": {"name": "Central African Republic", "flag": "🇨🇫"},
    "+235": {"name": "Chad", "flag": "🇹🇩"},
    "+56": {"name": "Chile", "flag": "🇨🇱"},
    "+86": {"name": "China", "flag": "🇨🇳"},
    "+57": {"name": "Colombia", "flag": "🇨🇴"},
    "+269": {"name": "Comoros", "flag": "🇰🇲"},
    "+243": {"name": "Democratic Republic of the Congo", "flag": "🇨🇩"},
    "+242": {"name": "Republic of the Congo", "flag": "🇨🇬"},
    "+506": {"name": "Costa Rica", "flag": "🇨🇷"},
    "+385": {"name": "Croatia", "flag": "🇭🇷"},
    "+53": {"name": "Cuba", "flag": "🇨🇺"},
    "+357": {"name": "Cyprus", "flag": "🇨🇾"},
    "+420": {"name": "Czech Republic", "flag": "🇨🇿"},
    "+45": {"name": "Denmark", "flag": "🇩🇰"},
    "+253": {"name": "Djibouti", "flag": "🇩🇯"},
    "+1-767": {"name": "Dominica", "flag": "🇩🇲"},
    "+1-809": {"name": "Dominican Republic", "flag": "🇩🇴"},
    "+670": {"name": "East Timor", "flag": "🇹🇱"},
    "+593": {"name": "Ecuador", "flag": "🇪🇨"},
    "+20": {"name": "Egypt", "flag": "🇪🇬"},
    "+503": {"name": "El Salvador", "flag": "🇸🇻"},
    "+240": {"name": "Equatorial Guinea", "flag": "🇬🇶"},
    "+291": {"name": "Eritrea", "flag": "🇪🇷"},
    "+372": {"name": "Estonia", "flag": "🇪🇪"},
    "+251": {"name": "Ethiopia", "flag": "🇪🇹"},
    "+298": {"name": "Faroe Islands", "flag": "🇫🇴"},
    "+679": {"name": "Fiji", "flag": "🇫🇯"},
    "+358": {"name": "Finland", "flag": "🇫🇮"},
    "+33": {"name": "France", "flag": "🇫🇷"},
    "+241": {"name": "Gabon", "flag": "🇬🇦"},
    "+220": {"name": "Gambia", "flag": "🇬🇲"},
    "+995": {"name": "Georgia", "flag": "🇬🇪"},
    "+49": {"name": "Germany", "flag": "🇩🇪"},
    "+233": {"name": "Ghana", "flag": "🇬🇭"},
    "+30": {"name": "Greece", "flag": "🇬🇷"},
    "+1-473": {"name": "Grenada", "flag": "🇬🇩"},
    "+502": {"name": "Guatemala", "flag": "🇬🇹"},
    "+224": {"name": "Guinea", "flag": "🇬🇳"},
    "+245": {"name": "Guinea-Bissau", "flag": "🇬🇼"},
    "+592": {"name": "Guyana", "flag": "🇬🇾"},
    "+509": {"name": "Haiti", "flag": "🇭🇹"},
    "+504": {"name": "Honduras", "flag": "🇭🇳"},
    "+36": {"name": "Hungary", "flag": "🇭🇺"},
    "+354": {"name": "Iceland", "flag": "🇮🇸"},
    "+91": {"name": "India", "flag": "🇮🇳"},
    "+62": {"name": "Indonesia", "flag": "🇮🇩"},
    "+98": {"name": "Iran", "flag": "🇮🇷"},
    "+964": {"name": "Iraq", "flag": "🇮🇶"},
    "+353": {"name": "Ireland", "flag": "🇮🇪"},
    "+972": {"name": "Israel", "flag": "🇮🇱"},
    "+39": {"name": "Italy", "flag": "🇮🇹"},
    "+1-876": {"name": "Jamaica", "flag": "🇯🇲"},
    "+81": {"name": "Japan", "flag": "🇯🇵"},
    "+962": {"name": "Jordan", "flag": "🇯🇴"},
    "+7": {"name": "Kazakhstan", "flag": "🇰🇿"},
    "+254": {"name": "Kenya", "flag": "🇰🇪"},
    "+686": {"name": "Kiribati", "flag": "🇰🇮"},
    "+850": {"name": "North Korea", "flag": "🇰🇵"},
    "+82": {"name": "South Korea", "flag": "🇰🇷"},
    "+965": {"name": "Kuwait", "flag": "🇰🇼"},
    "+996": {"name": "Kyrgyzstan", "flag": "🇰🇬"},
    "+856": {"name": "Laos", "flag": "🇱🇦"},
    "+371": {"name": "Latvia", "flag": "🇱🇻"},
    "+961": {"name": "Lebanon", "flag": "🇱🇧"},
    "+266": {"name": "Lesotho", "flag": "🇱🇸"},
    "+231": {"name": "Liberia", "flag": "🇱🇷"},
    "+218": {"name": "Libya", "flag": "🇱🇾"},
    "+423": {"name": "Liechtenstein", "flag": "🇱🇮"},
    "+370": {"name": "Lithuania", "flag": "🇱🇹"},
    "+352": {"name": "Luxembourg", "flag": "🇱🇺"},
    "+261": {"name": "Madagascar", "flag": "🇲🇬"},
    "+265": {"name": "Malawi", "flag": "🇲🇼"},
    "+60": {"name": "Malaysia", "flag": "🇲🇾"},
    "+960": {"name": "Maldives", "flag": "🇲🇻"},
    "+223": {"name": "Mali", "flag": "🇲🇱"},
    "+356": {"name": "Malta", "flag": "🇲🇹"},
    "+692": {"name": "Marshall Islands", "flag": "🇲🇭"},
    "+222": {"name": "Mauritania", "flag": "🇲🇷"},
    "+230": {"name": "Mauritius", "flag": "🇲🇺"},
    "+52": {"name": "Mexico", "flag": "🇲🇽"},
    "+691": {"name": "Micronesia", "flag": "🇫🇲"},
    "+373": {"name": "Moldova", "flag": "🇲🇩"},
    "+377": {"name": "Monaco", "flag": "🇲🇨"},
    "+976": {"name": "Mongolia", "flag": "🇲🇳"},
    "+382": {"name": "Montenegro", "flag": "🇲🇪"},
    "+212": {"name": "Morocco", "flag": "🇲🇦"},
    "+258": {"name": "Mozambique", "flag": "🇲🇿"},
    "+95": {"name": "Myanmar", "flag": "🇲🇲"},
    "+264": {"name": "Namibia", "flag": "🇳🇦"},
    "+674": {"name": "Nauru", "flag": "🇳🇷"},
    "+977": {"name": "Nepal", "flag": "🇳🇵"},
    "+31": {"name": "Netherlands", "flag": "🇳🇱"},
    "+64": {"name": "New Zealand", "flag": "🇳🇿"},
    "+505": {"name": "Nicaragua", "flag": "🇳🇮"},
    "+227": {"name": "Niger", "flag": "🇳🇪"},
    "+234": {"name": "Nigeria", "flag": "🇳🇬"},
    "+47": {"name": "Norway", "flag": "🇳🇴"},
    "+968": {"name": "Oman", "flag": "🇴🇲"},
    "+92": {"name": "Pakistan", "flag": "🇵🇰"},
    "+680": {"name": "Palau", "flag": "🇵🇼"},
    "+507": {"name": "Panama", "flag": "🇵🇦"},
    "+675": {"name": "Papua New Guinea", "flag": "🇵🇬"},
    "+595": {"name": "Paraguay", "flag": "🇵🇾"},
    "+51": {"name": "Peru", "flag": "🇵🇪"},
    "+63": {"name": "Philippines", "flag": "🇵🇭"},
    "+48": {"name": "Poland", "flag": "🇵🇱"},
    "+351": {"name": "Portugal", "flag": "🇵🇹"},
    "+974": {"name": "Qatar", "flag": "🇶🇦"},
    "+40": {"name": "Romania", "flag": "🇷🇴"},
    "+7": {"name": "Russia", "flag": "🇷🇺"},
    "+250": {"name": "Rwanda", "flag": "🇷🇼"},
    "+1-869": {"name": "Saint Kitts and Nevis", "flag": "🇰🇳"},
    "+1-758": {"name": "Saint Lucia", "flag": "🇱🇨"},
    "+1-784": {"name": "Saint Vincent and the Grenadines", "flag": "🇻🇨"},
    "+685": {"name": "Samoa", "flag": "🇼🇸"},
    "+378": {"name": "San Marino", "flag": "🇸🇲"},
    "+239": {"name": "Sao Tome and Principe", "flag": "🇸🇹"},
    "+966": {"name": "Saudi Arabia", "flag": "🇸🇦"},
    "+221": {"name": "Senegal", "flag": "🇸🇳"},
    "+381": {"name": "Serbia", "flag": "🇷🇸"},
    "+248": {"name": "Seychelles", "flag": "🇸🇨"},
    "+232": {"name": "Sierra Leone", "flag": "🇸🇱"},
    "+65": {"name": "Singapore", "flag": "🇸🇬"},
    "+421": {"name": "Slovakia", "flag": "🇸🇰"},
    "+386": {"name": "Slovenia", "flag": "🇸🇮"},
    "+677": {"name": "Solomon Islands", "flag": "🇸🇧"},
    "+252": {"name": "Somalia", "flag": "🇸🇴"},
    "+27": {"name": "South Africa", "flag": "🇿🇦"},
    "+211": {"name": "South Sudan", "flag": "🇸🇸"},
    "+34": {"name": "Spain", "flag": "🇪🇸"},
    "+94": {"name": "Sri Lanka", "flag": "🇱🇰"},
    "+249": {"name": "Sudan", "flag": "🇸🇩"},
    "+597": {"name": "Suriname", "flag": "🇸🇷"},
    "+268": {"name": "Swaziland", "flag": "🇸🇿"},
    "+46": {"name": "Sweden", "flag": "🇸🇪"},
    "+41": {"name": "Switzerland", "flag": "🇨🇭"},
    "+963": {"name": "Syria", "flag": "🇸🇾"},
    "+886": {"name": "Taiwan", "flag": "🇹🇼"},
    "+992": {"name": "Tajikistan", "flag": "🇹🇯"},
    "+255": {"name": "Tanzania", "flag": "🇹🇿"},
    "+66": {"name": "Thailand", "flag": "🇹🇭"},
    "+228": {"name": "Togo", "flag": "🇹🇬"},
    "+676": {"name": "Tonga", "flag": "🇹🇴"},
    "+1-868": {"name": "Trinidad and Tobago", "flag": "🇹🇹"},
    "+216": {"name": "Tunisia", "flag": "🇹🇳"},
    "+90": {"name": "Turkey", "flag": "🇹🇷"},
    "+993": {"name": "Turkmenistan", "flag": "🇹🇲"},
    "+1-649": {"name": "Turks and Caicos Islands", "flag": "🇹🇨"},
    "+688": {"name": "Tuvalu", "flag": "🇹🇻"},
    "+256": {"name": "Uganda", "flag": "🇺🇬"},
    "+380": {"name": "Ukraine", "flag": "🇺🇦"},
    "+971": {"name": "United Arab Emirates", "flag": "🇦🇪"},
    "+44": {"name": "United Kingdom", "flag": "🇬🇧"},
    "+1": {"name": "United States", "flag": "🇺🇸"},
    "+598": {"name": "Uruguay", "flag": "🇺🇾"},
    "+998": {"name": "Uzbekistan", "flag": "🇺🇿"},
    "+678": {"name": "Vanuatu", "flag": "🇻🇺"},
    "+379": {"name": "Vatican City", "flag": "🇻🇦"},
    "+58": {"name": "Venezuela", "flag": "🇻🇪"},
    "+84": {"name": "Vietnam", "flag": "🇻🇳"},
    "+967": {"name": "Yemen", "flag": "🇾🇪"},
    "+260": {"name": "Zambia", "flag": "🇿🇲"},
    "+263": {"name": "Zimbabwe", "flag": "🇿🇼"},
}

def get_country_info(code):
    return COUNTRY_INFO.get(code, {"name": code, "flag": ""})

@bot.message_handler(commands=['cap'])
@require_channel_membership
def handle_cap(message):
    countries = get_country_capacities()
    
    # Escape function for MarkdownV2
    def escape_md_v2(text):
        chars_to_escape = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in chars_to_escape:
            text = text.replace(char, f'\\{char}')
        return text
    
    # Header with emoji and title in bold
    header = "🔋 *Available Countries*\n"
    header += "────────────────\n\n"
    
    # Sort countries by country code
    sorted_countries = sorted(countries, key=lambda x: x['country_code'])
    
    # Build country entries
    country_lines = []
    for c in sorted_countries:
        code = c['country_code']
        info = get_country_info(code)
        flag = info['flag']
        free_spam = c.get('free_spam', c.get('price', 0.0))
        claim_time = c.get('claim_time', 300)
        
        # Escape special characters for MarkdownV2
        code_escaped = escape_md_v2(code)
        price_escaped = escape_md_v2(str(free_spam))
        claim_time_escaped = escape_md_v2(str(claim_time))
        
        # Each country in its own blockquote with copyable code
        country_lines.append(f"> {flag} `{code_escaped}` \\| \\$ {price_escaped}\\$ \\| \\$ {claim_time_escaped}s")

    # Combine all parts - need empty line between blockquotes to keep them separate
    full_message = (
        header +
        "\n\n".join(country_lines) +
        "\n\n────────────────\n" +
        f"🌍 *Total Countries*: {len(countries)}\n\n"
    )
    
    bot.send_message(message.chat.id, full_message, parse_mode="MarkdownV2")
