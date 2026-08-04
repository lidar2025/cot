#!/usr/bin/env python3
"""
يسحب بيانات Disaggregated COT من CFTC عبر Socrata API، يصفي رموز الذهب/اليورو/البتكوين،
ويحفظها بصيغة JSON مبسطة بملف cot.json بجذر المستودع.
يشتغل من داخل GitHub Actions (IP رينرات GitHub، مو Cloudflare Workers).
"""
import json
import urllib.request
import urllib.parse

CODES = {
    "088691": "XAU/USD",
    "099741": "EUR/USD",
    "133741": "BTC/USD",
}

BASE_URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"


def p(row):
    oi = int(row.get("open_interest_all") or 1)
    cl = int(row.get("prod_merc_positions_long") or 0)
    cs = int(row.get("prod_merc_positions_short") or 0)
    sl = int(row.get("swap_positions_long_all") or 0)
    ss = int(row.get("swap__positions_short_all") or 0)
    ml = int(row.get("m_money_positions_long_all") or 0)
    ms = int(row.get("m_money_positions_short_all") or 0)
    ol = int(row.get("other_rept_positions_long") or 0)
    os_ = int(row.get("other_rept_positions_short") or 0)

    def pct(a, b):
        return round(((a - b) / oi) * 100)

    return {
        "date": (row.get("report_date_as_yyyy_mm_dd") or "")[:10],
        "openInterest": oi,
        "commercial": {"long": cl, "short": cs, "net": cl - cs, "pct": pct(cl, cs)},
        "managedMoney": {"long": ml, "short": ms, "net": ml - ms, "pct": pct(ml, ms)},
        "swapDealers": {"long": sl, "short": ss, "net": sl - ss, "pct": pct(sl, ss)},
        "other": {"long": ol, "short": os_, "net": ol - os_, "pct": pct(ol, os_)},
    }


def main():
    codes_list = ",".join(f"'{c}'" for c in CODES)
    where_clause = f"cftc_contract_market_code in({codes_list})"
    params = {
        "$where": where_clause,
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": "50",
    }
    url = BASE_URL + "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        rows = json.loads(resp.read().decode("utf-8"))

    out = {}
    seen = set()
    for row in rows:
        code = row.get("cftc_contract_market_code")
        label = CODES.get(code)
        if not label or label in seen:
            continue
        seen.add(label)
        out[label] = p(row)

    with open("cot.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
