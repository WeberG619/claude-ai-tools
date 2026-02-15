# Agent Team Business Recommendation
## For: Weber Gouin | Date: February 3, 2026

---

## Executive Summary

After extensive research and team deliberation, we recommend a **dual-income strategy**:

1. **Primary Business**: Construction Photo Intelligence SaaS
2. **Secondary Income**: Prediction Market Arbitrage Bot

---

## Primary Recommendation: Construction Photo Intelligence

### The Problem
Every construction project generates thousands of site photos. They end up in messy folders with names like `IMG_4521.jpg`. Finding the right photo for a punch list, inspection, or dispute resolution is a nightmare.

### The Solution
An AI-powered platform that:
- Automatically tags photos with room names, materials, defects, progress stages
- Links photos to project locations (floor plans, BIM models)
- Generates organized photo reports for submittals and documentation
- Identifies potential code violations and punch list items

### Why This Works

| Factor | Advantage |
|--------|-----------|
| **Market Size** | Construction SaaS: $16.3B → $45.5B by 2035 |
| **Competition** | Fragmented - top 5 players hold only 12% |
| **Domain Expertise** | Weber knows AEC workflows intimately |
| **Tech Maturity** | OpenAI Vision API is production-ready |
| **Universal Pain Point** | Every GC, architect, inspector has this problem |
| **Recurring Revenue** | Monthly SaaS subscription per project |

### Revenue Model
- **Pricing**: $30-100/month per active project
- **Target**: Small to mid-size GCs and architecture firms
- **Upsell**: Premium features (BIM integration, AI defect detection)

### MVP Features (Phase 1)
1. Photo upload (drag & drop or mobile app)
2. AI auto-tagging (room, floor, trade, date)
3. Search and filter interface
4. Basic report generation
5. Project organization dashboard

### Tech Stack
- **Backend**: Python/FastAPI
- **AI**: OpenAI Vision API (GPT-4 Vision)
- **Storage**: AWS S3 or Cloudflare R2
- **Frontend**: React or simple web interface
- **Auth**: Clerk or Auth0

### Estimated Timeline
- Week 1-2: Core API and AI tagging
- Week 3-4: Web interface and upload
- Week 5-6: Report generation and polish
- Week 7-8: Beta testing with real users

### Estimated Costs
- OpenAI API: ~$0.01-0.03 per image
- Cloud hosting: ~$50-100/month to start
- Domain/misc: ~$50

---

## Secondary Recommendation: Prediction Market Arbitrage

### The Opportunity
Academic research documented **$40+ million in arbitrage profits** extracted from prediction markets between April 2024 and April 2025.

### How It Works
Prediction markets like Polymarket and Kalshi price binary outcomes (Yes/No).
When the combined cost of Yes + No across platforms < $1.00, you profit regardless of outcome.

Example:
- Polymarket: "Event X happens" YES = $0.52
- Kalshi: "Event X happens" NO = $0.45
- Combined cost: $0.97
- Guaranteed profit: $0.03 (3%)

### Key Requirements
- **Automation**: Manual trading is impossible - spreads close in seconds
- **APIs**: Both platforms have APIs for programmatic trading
- **Capital**: Start small ($500-1000) to test
- **Monitoring**: Real-time price feeds and execution

### Risks
| Risk | Mitigation |
|------|------------|
| Different resolution criteria | Only trade high-certainty markets |
| Platform regulatory issues | Kalshi is CFTC-regulated (safer) |
| Spread compression | Focus on event-driven markets |
| Technical failures | Robust error handling, small positions |

### Realistic Returns
- Spreads: 0.5% - 3% typically
- Frequency: Depends on market activity
- Expected: $50-500/month with small capital
- Scales with capital and sophistication

### Tech Stack
- Python bot monitoring both APIs
- Real-time price comparison
- Automatic execution when spread detected
- Logging and P&L tracking

---

## Implementation Roadmap

### Month 1: Foundation
- [ ] Build MVP of photo tagging tool
- [ ] Set up prediction market bot (paper trading)
- [ ] Identify 5 beta users for photo tool

### Month 2: Validation
- [ ] Beta test photo tool with real projects
- [ ] Go live with small capital on arbitrage bot
- [ ] Iterate based on feedback

### Month 3: Growth
- [ ] Launch photo tool publicly
- [ ] Begin marketing to AEC firms
- [ ] Scale arbitrage bot if profitable

---

## Research Sources

### Market Data
- [Construction SaaS Market Report](https://www.gminsights.com/industry-analysis/construction-software-as-a-service-market)
- [2026 Engineering and Construction Outlook - Deloitte](https://www.deloitte.com/us/en/insights/industry/engineering-and-construction/engineering-and-construction-industry-outlook.html)
- [Vertical SaaS Trends 2026](https://baltech.in/blog/why-vertical-saas-is-winning-2026-industry-software-integration/)

### Prediction Markets
- [Prediction Market Arbitrage Guide](https://newyorkcityservers.com/blog/prediction-market-arbitrage-guide)
- [NPR: How Prediction Market Traders Make Money](https://www.npr.org/2026/01/17/nx-s1-5672615/kalshi-polymarket-prediction-market-boom-traders-slang-glossary)
- [Arbitrage Opportunities in Prediction Markets](https://www.ainvest.com/news/arbitrage-opportunities-prediction-markets-smart-money-profits-price-inefficiencies-polymarket-2512/)

### Freelance & Business Models
- [Upwork: Highest-Paying Freelance Jobs 2026](https://www.upwork.com/resources/highest-paying-freelance-jobs)
- [Shopify: Most Profitable Businesses 2026](https://www.shopify.com/blog/most-profitable-businesses)

---

## Team Consensus

| Agent | Vote | Notes |
|-------|------|-------|
| **Planner (Andrew)** | ✅ Photo SaaS | "Sustainable recurring revenue with domain advantage" |
| **Researcher (Guy)** | ✅ Photo SaaS | "88% of market up for grabs by niche players" |
| **Builder (Christopher)** | ✅ Both | "MVP in weeks, arbitrage bot as side project" |
| **Critic (Eric)** | ✅ Both | "Diversified risk, two income streams" |
| **Narrator (Jenny)** | — | Summary role |

---

## Next Steps

1. **Decide**: Which path(s) to pursue
2. **Prototype**: We can start building immediately
3. **Validate**: Find 3-5 beta users in your network
4. **Launch**: Get to market fast, iterate based on feedback

**The team is ready to build. What's your call, Weber?**
