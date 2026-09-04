<div align="center">
  <img src="./assets/banner.svg" width="100%" alt="Dhruv Gupta, Full-Stack Developer and AI/ML Engineer" />
</div>

<br/>

## About

I work on the seam between messy inputs and systems people can trust. Most of what I build reduces to the same problem in different clothes: a question arrives in a form a database cannot answer, and something has to turn it into a query, a vector, or a frame.

That has meant embedding food-service catalogues so a search understands intent rather than keywords, running a ResNet50 gaze estimator fast enough that a webcam feels responsive, and consolidating oil-well maintenance logs at ONGC that had lived in five departments and no single place. The through line is not the framework. It is caring whether the thing is still correct at eight million rows and still fast on the hundredth query.

Right now that instinct is pointed at enterprise data migration at Deloitte, where correctness under scale is the entire job rather than a nice-to-have.

> [!NOTE]
> **Currently building**
>
> - A **training and placement portal** for Manipal University Jaipur. Placement season is run on spreadsheets and WhatsApp threads at most colleges. This replaces that with role-based access, eligibility rules that filter applications automatically, and an audit trail for every status change.
> - **Retrieval infrastructure**: embeddings, hybrid search, and the unglamorous work of grounding model output in data that can actually be cited.
> - Deepening **SAP ABAP and HANA** on the enterprise side, migrating legacy structures without losing history.

<br/>

## How I got here

```mermaid
gantt
    title  From coursework to production systems
    dateFormat  YYYY-MM
    axisFormat  %Y
    tickInterval 1year
    todayMarker off

    section Education
    B.Tech CSE, IoT and Intelligent Systems, MUJ   :done, edu, 2022-09, 2026-05

    section Recognition
    Mettl CodeRush, Round 2                        :milestone, m1, 2024-03, 0d
    Adobe GenSolve, Round 2                        :milestone, m2, 2024-05, 0d
    SAP India Hackfest, Top 50 of 2000+            :milestone, m3, 2024-07, 0d

    section Industry
    ONGC, Summer Intern, SAP ABAP and HANA         :done, ongc, 2025-06, 2025-08
    Deloitte, Data Migration and Modernization     :active, dl, 2026-01, 2026-12
```

### What each of those actually involved

<table>
<tr>
<td width="30%" valign="top"><b>Deloitte</b><br/><sub>Data Migration and Modernization Analyst<br/>2026 to present</sub></td>
<td valign="top">Moving enterprise data between legacy and modern SAP structures. The interesting constraint is that a migration is judged entirely on what it did <em>not</em> lose, so most of the effort goes into reconciliation and verification rather than transfer.</td>
</tr>
<tr>
<td valign="top"><b>ONGC</b><br/><sub>Summer Intern, Delhi<br/>Jun to Aug 2025</sub></td>
<td valign="top">Built a centralised SAP ABAP and HANA dashboard for oil well management, replacing manual reporting that was spread across five departments. Cut reporting time by <b>40%</b> and preprocessed <b>8M+ records</b> using Python, FAISS and PyTorch to make historical logs searchable.</td>
</tr>
<tr>
<td valign="top"><b>SAP India Hackfest</b><br/><sub>National Finalist<br/>Jul 2024</sub></td>
<td valign="top">Led a team of five to a <b>Top 50 finish from 2000+ entries</b>, building EcoHive, a sustainable credit trading platform. Most of the learning was in scoping: deciding what to cut so the remaining thing worked end to end.</td>
</tr>
<tr>
<td valign="top"><b>Manipal University Jaipur</b><br/><sub>B.Tech CSE, IoT and Intelligent Systems<br/>2022 to 2026, CGPA 8.06</sub></td>
<td valign="top">Data structures, DBMS, operating systems and machine learning, plus the placement portal above, which turned out to teach more about requirements than any course did.</td>
</tr>
</table>

<br/>

## Toolkit

Grouped by where I have actually shipped it, not by what I have read about.

| Domain | Tools | Shipped in |
| :--- | :--- | :--- |
| **Backend** | Python, FastAPI, Node.js, Go | Semantic search API, multi-agent NLP service |
| **Data** | PostgreSQL, pgvector, Redis, FAISS | Vector retrieval at sub-100ms, 8M+ record preprocessing |
| **AI / ML** | PyTorch, TensorFlow, OpenCV, MediaPipe, scikit-learn | Real-time gaze estimation at 30 FPS, transformer embeddings |
| **Frontend** | React, Next.js, TypeScript, Tailwind | Placement portal, EcoHive, this portfolio |
| **Enterprise** | SAP ABAP, HANA DB | ONGC well-management dashboard, Deloitte migrations |
| **Platform** | Docker, Git, GitHub Actions, Vercel | Containerised services, CI for every repo above |

<br/>

## By the numbers

These update themselves daily from the GitHub GraphQL API. Nothing here is hand-typed.

<!-- snapshot starts -->
| | |
| :--- | ---: |
| Contributions, last 12 months | **—** |
| Current streak | **—** |
_Run the workflow once to populate this._
<!-- snapshot ends -->

### Where the code goes

<!-- languages starts -->
| Language | Share | |
| :--- | :--- | ---: |
| **—** | `░░░░░░░░░░░░░░░░░░░░░░` | — |
<!-- languages ends -->

### When I actually commit

<!-- rhythm starts -->
| Time of day (IST) | Window | Commits | |
| :--- | :--- | ---: | :--- |
| **—** | | | |
<!-- rhythm ends -->

<br/>

## Certifications

Less a badge collection than a deliberate path: get the data layer right, learn to look at data before modelling it, then move up into supervised learning and generative systems.

```mermaid
flowchart LR
    A["SQL<br/><small>IBM · Apr 2024</small>"] --> B["Exploratory<br/>Data Analysis<br/><small>IBM · Nov 2024</small>"]
    A --> C["Foundations of<br/>Data Science<br/><small>Google · Nov 2024</small>"]
    B --> D["Supervised<br/>Machine Learning<br/><small>IBM · Dec 2024</small>"]
    C --> D
    D --> E["Generative AI<br/>Fundamentals<br/><small>IBM · Apr 2025</small>"]
    F["Software Engineering:<br/>Implementation & Testing<br/><small>HKUST · Nov 2024</small>"] --> E
```

<details>
<summary><b>Verification links</b></summary>

<br/>

| Credential | Issuer | Date | |
| :--- | :--- | :--- | :--- |
| Generative AI Fundamentals Specialization | IBM | Apr 2025 | [Verify](https://www.coursera.org/account/accomplishments/specialization/3J6F007VM0D8) |
| Supervised Machine Learning | IBM | Dec 2024 | [Verify](https://www.coursera.org/account/accomplishments/verify/6I9AJ3Y0BVUG) |
| Exploratory Data Analysis for Machine Learning | IBM | Nov 2024 | [Verify](https://www.coursera.org/account/accomplishments/verify/1PHJMYY9JZGU) |
| Foundations of Data Science | Google | Nov 2024 | [Verify](https://www.coursera.org/account/accomplishments/verify/Q90KYBSORZ5M) |
| Software Engineering: Implementation and Testing | HKUST | Nov 2024 | [Verify](https://www.coursera.org/account/accomplishments/verify/DI0V4MISJN3G) |
| SQL: A Practical Introduction | IBM | Apr 2024 | [Verify](https://www.coursera.org/account/accomplishments/verify/SP4VAYZD688E) |

</details>

<br/>

## Get in touch

Open to AI/ML and full-stack collaboration, and happy to talk through anything above in more detail.

<a href="https://dhruvgupta-nu.vercel.app"><img src="https://img.shields.io/badge/Portfolio-0F172A?style=for-the-badge&logo=vercel&logoColor=818CF8" alt="Portfolio" /></a>
<a href="https://www.linkedin.com/in/dhruvgpta/"><img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn" /></a>
<a href="mailto:dhruvgupta6580@gmail.com"><img src="https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="Email" /></a>
<a href="https://dhruvgupta-nu.vercel.app/Dhruv_resume.pdf"><img src="https://img.shields.io/badge/Résumé-0F172A?style=for-the-badge&logo=readdotcv&logoColor=818CF8" alt="Resume" /></a>

<br/><br/>

<sub><!-- updated starts -->_Not yet refreshed._<!-- updated ends --></sub>
