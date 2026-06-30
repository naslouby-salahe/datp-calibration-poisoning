# Springer LNCS LaTeX2e Proceedings Template Guidelines

This guideline summarizes how to prepare a paper using the Springer `llncs` LaTeX2e class from the provided template package.

Source package inspected:

* `llncs.cls` — Springer LNCS LaTeX2e document class.
* `llncsdoc.pdf` — official class documentation.
* `samplepaper.tex` — sample LNCS paper template.
* `splncs04.bst` — Springer LNCS BibTeX bibliography style.
* `fig1.eps` — sample figure used by the template.
* `history.txt` — package version history.
* `readme.txt` — package file list and purpose.

---

## 1. Purpose of the Template

Use this package for Springer Lecture Notes in Computer Science, LNCS, and related Springer computer science proceedings series.

The `llncs` class is based on the standard LaTeX `article` class, but it fixes the layout, heading styles, caption styles, metadata commands, theorem environments, and bibliography behavior expected by Springer proceedings.

The class already controls the page layout. Do not manually redesign the document.

---

## 2. Required Files

Keep the following files in your LaTeX project directory unless your TeX installation already provides them globally:

```text
llncs.cls
splncs04.bst
```

Recommended project structure:

```text
paper/
├── main.tex
├── references.bib
├── llncs.cls
├── splncs04.bst
├── figures/
│   ├── figure1.eps
│   └── figure2.pdf
└── sections/
    ├── introduction.tex
    ├── method.tex
    ├── results.tex
    └── conclusion.tex
```

If you use only one LaTeX file, `main.tex` is enough.

---

## 3. Basic Document Setup

Use the `llncs` document class, not `article`.

Recommended starting point:

```latex
\documentclass[runningheads]{llncs}

\usepackage[T1]{fontenc}
\usepackage{graphicx}

\begin{document}

\title{Your Paper Title}
\titlerunning{Short Paper Title}

\author{
First Author\inst{1}\orcidID{0000-1111-2222-3333}
\and
Second Author\inst{2}\orcidID{1111-2222-3333-4444}
}

\authorrunning{F. Author et al.}

\institute{
First Institution, City, Country\\
\email{first.author@example.com}
\and
Second Institution, City, Country\\
\email{second.author@example.com}
}

\maketitle

\begin{abstract}
Write a concise abstract of 150--250 words.

\keywords{First Keyword \and Second Keyword \and Third Keyword}
\end{abstract}

\section{Introduction}

Your text starts here.

\begin{credits}
\subsubsection{\ackname}
Optional acknowledgments go here.

\subsubsection{\discintname}
The authors have no competing interests to declare that are relevant to the content of this article.
\end{credits}

\bibliographystyle{splncs04}
\bibliography{references}

\end{document}
```

---

## 4. Class Options

### 4.1 Recommended Option

Use `runningheads` when the proceedings require running heads:

```latex
\documentclass[runningheads]{llncs}
```

Then define shortened running heads when needed:

```latex
\titlerunning{Short Paper Title}
\authorrunning{F. Author et al.}
```

### 4.2 Author-Year Citation Option

Use this only if the proceedings or editor explicitly requires author-year citations:

```latex
\documentclass[citeauthoryear]{llncs}
```

This option does not automatically convert your citations into author-year style. It changes how `\bibitem` can display years. You still need to write the surrounding author names and punctuation manually where appropriate.

### 4.3 Obsolete or Special-Case Options

Avoid these unless you have a specific compatibility reason.

| Option          | Meaning                                                                             | Recommendation                                         |
| --------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `orivec`        | Restores the original LaTeX arrow-style `\vec` instead of LNCS bold italic vectors. | Avoid unless arrow vectors are required.               |
| `envcountsame`  | Makes theorem-like environments share one counter.                                  | Avoid unless the editor requires it.                   |
| `envcountreset` | Resets theorem-like counters per section.                                           | Avoid unless the editor requires it.                   |
| `envcountsect`  | Numbers theorem-like environments with section numbers.                             | Obsolete; avoid unless legacy compatibility is needed. |
| `openbib`       | Uses an open bibliography layout.                                                   | Avoid unless specifically requested.                   |
| `oribibl`       | Restores original LaTeX bibliography and citation behavior.                         | Use only for BibTeX compatibility problems.            |

---

## 5. Layout Rules

The class sets the official Springer LNCS layout automatically.

Important fixed layout values:

* Text width: `122 mm`.
* Text height: `193 mm`.
* Heading spacing, caption style, running heads, and theorem formatting are controlled by `llncs.cls`.

Do not change these manually:

```latex
\textwidth
\textheight
\topmargin
\oddsidemargin
\evensidemargin
\baselinestretch
\vspace
\hspace
```

Avoid these practices:

```latex
\vspace{-5mm}
\hspace{-3mm}
\renewcommand{\baselinestretch}{0.95}
\setlength{\textwidth}{...}
\setlength{\textheight}{...}
```

Springer expects the class to control the manuscript appearance.

---

## 6. Fonts and Encoding

Always load T1 font encoding:

```latex
\usepackage[T1]{fontenc}
```

Reason: T1 fonts help generate correct final print and online PDFs. Other encodings can cause incorrect characters, especially in accented names, metadata, copy-and-paste text, and indexing.

---

## 7. Title Rules

Use:

```latex
\title{Your Contribution Title}
```

Title formatting rules:

* Capitalize major words.
* Do not capitalize short conjunctions, prepositions, or articles unless they appear at the beginning.
* Examples of words usually not capitalized inside a title: `on`, `of`, `by`, `and`, `or`, `but`, `from`, `with`, `without`, `under`, `the`, `a`, `an`.
* Do not end the title with punctuation.
* Formula symbols should be written as they appear in normal text.
* If the title is too long for the running head, use `\titlerunning`.

Example:

```latex
\title{Device-Aware Threshold Personalization for Non-IID Federated IoT Malware Detection}
\titlerunning{Device-Aware Threshold Personalization}
```

### 7.1 Title Footnotes

If funding or support must be attached to the title, use `\thanks` inside `\title`:

```latex
\title{Your Contribution Title\thanks{This work was supported by Project X.}}
```

If multiple title footnotes are needed, separate them with `\fnmsep`.

Do not use `\thanks` inside `\author` or `\institute`. Footnotes for authors and institutes are not supported in the online version and may be dropped.

### 7.2 Subtitle

If a subtitle is needed, use:

```latex
\subtitle{Your Subtitle}
```

Use a subtitle only when it adds meaningful information and is accepted by the target proceedings.

---

## 8. Author Rules

Use:

```latex
\author{
First Author\inst{1}\orcidID{0000-1111-2222-3333}
\and
Second Author\inst{2,3}\orcidID{1111-2222-3333-4444}
}
```

Author formatting rules:

* Separate authors with `\and`.
* Use `\inst{...}` to connect authors to affiliations.
* Use comma-separated affiliation numbers for authors with multiple affiliations, for example `\inst{2,3}`.
* Put given name or given names before family name.
* Include ORCID identifiers when available using `\orcidID{...}`.
* Do not put email addresses in `\author`.
* Put email addresses in `\institute`.
* Do not use `\thanks` inside `\author`.

### 8.1 Family Names with Multiple Parts

If a family name has multiple parts, make the family name unambiguous.

Examples:

```latex
Jos\'{e} Martinez~Perez
Jos\'{e} {Martinez Perez}
```

This helps Springer correctly abbreviate names in running heads and author indexes.

### 8.2 Running Author Line

Use `\authorrunning` when the author list is too long or when initials may be ambiguous:

```latex
\authorrunning{F. Author et al.}
```

Rules:

* First names are abbreviated in running heads.
* If there are more than two authors, use `et al.` when appropriate.
* Keep the running author line short enough to fit on one line.

---

## 9. Affiliation Rules

Use `\institute` for institutions, emails, and URLs:

```latex
\institute{
Institution One, City, Country\\
\email{author1@example.com}
\and
Institution Two, City, Country\\
\email{author2@example.com}\\
\url{https://example.org}
}
```

Affiliation rules:

* Separate multiple affiliations with `\and`.
* Use `\email{...}` for email addresses.
* Use `\url{...}` for web pages.
* Make sure email order matches the order of authors affiliated with that institution.
* Be aware that email addresses may appear in the online metadata of the published version.
* Do not put author footnotes in `\institute`.

If you need a tilde in a homepage path, use `\homedir` instead of typing a raw tilde.

---

## 10. Header Generation

After defining title, authors, affiliations, and running heads, call:

```latex
\maketitle
```

This command prints the paper header. If `\maketitle` is missing, the title, author, and institute information will not appear in the document body.

Correct order:

```latex
\title{...}
\titlerunning{...}
\author{...}
\authorrunning{...}
\institute{...}
\maketitle
```

---

## 11. Abstract and Keywords

Use the `abstract` environment immediately after `\maketitle`:

```latex
\begin{abstract}
The abstract should briefly summarize the contents of the paper in 150--250 words.

\keywords{First Keyword \and Second Keyword \and Third Keyword}
\end{abstract}
```

Abstract rules:

* Recommended length: 150--250 words.
* State the problem, method, main result, and implication clearly.
* Avoid citations unless absolutely necessary.
* Avoid undefined acronyms.
* Avoid tables, figures, displayed equations, and bullet lists.

Keyword rules:

* Put `\keywords{...}` inside the `abstract` environment.
* Capitalize the first letter of each keyword.
* Separate keywords with `\and`, not commas.
* The class renders the separator correctly.

Correct:

```latex
\keywords{Federated Learning \and IoT Malware Detection \and Calibration Poisoning}
```

Avoid:

```latex
\keywords{federated learning, IoT malware detection, calibration poisoning}
```

---

## 12. Section and Heading Rules

Use standard LaTeX sectioning commands:

```latex
\section{Introduction}
\subsection{Motivation}
\subsubsection{Main Observation}
\paragraph{Implementation Detail}
```

Rules:

* Use no more than four heading levels.
* Only the first two levels are numbered by default.
* Lower-level headings are formatted as run-in headings.
* The first paragraph after a section or subsection is not indented.
* The first paragraph after a table, figure, or equation also does not need indentation.
* Subsequent paragraphs are indented automatically.
* Do not manually force indentation or remove indentation unless there is a clear typographic reason.

Recommended structure for a research paper:

```latex
\section{Introduction}
\section{Related Work}
\section{Method}
\section{Experimental Setup}
\section{Results}
\section{Discussion}
\section{Conclusion}
```

For short conference papers, merge sections when needed instead of creating many thin sections.

---

## 13. Paragraph Rules

Normal paragraphs should be written as plain LaTeX text.

Correct:

```latex
This paragraph introduces the method and explains the main idea.

This second paragraph continues with implementation details.
```

Avoid excessive manual spacing:

```latex
This paragraph ends here.\\[2mm]
\indent This paragraph is manually indented.
```

Let the class handle spacing and indentation.

---

## 14. Tables

Use standard LaTeX table floats:

```latex
\begin{table}
\caption{Table captions should be placed above the table.}
\label{tab:results}
\begin{tabular}{lrr}
\hline
Method & Macro-F1 & AUROC \\
\hline
Baseline & 0.91 & 0.98 \\
Proposed & 0.94 & 0.99 \\
\hline
\end{tabular}
\end{table}
```

Table rules:

* Place table captions above tables.
* Put `\label{...}` after `\caption{...}`.
* Reference tables with `Table~\ref{tab:results}`.
* Use clear column names and units.
* Avoid oversized tables that exceed the text width.
* Do not use screenshots of tables.
* Avoid tiny fonts unless absolutely necessary.
* Keep tables readable in grayscale.

---

## 15. Figures

Load `graphicx`:

```latex
\usepackage{graphicx}
```

Use standard figure floats:

```latex
\begin{figure}
\includegraphics[width=\textwidth]{figures/architecture.eps}
\caption{A figure caption is placed below the illustration.}
\label{fig:architecture}
\end{figure}
```

Figure rules:

* Place figure captions below figures.
* Put `\label{...}` after `\caption{...}`.
* Reference figures with `Fig.~\ref{fig:architecture}`.
* Prefer vector graphics for diagrams, architecture figures, plots, and line art.
* Avoid rasterized images for diagrams and schemas.
* EPS is preferred by the sample template when possible.
* Ensure all text inside figures is readable at final LNCS size.
* Avoid color-only distinctions; use line styles, markers, or labels as well.
* Keep figures within `\textwidth` unless there is a strong reason not to.

Practical note:

* If compiling with a LaTeX route that supports EPS, EPS figures are acceptable.
* If compiling with `pdflatex`, convert EPS figures to PDF first or enable a proper EPS-to-PDF workflow.

---

## 16. Equations

Displayed equations should be centered and placed on their own line:

```latex
\begin{equation}
x + y = z
\end{equation}
```

Equation rules:

* Use numbered equations only when they are referenced later.
* Reference equations with `Eq.~\ref{eq:example}`.
* Use `\label{...}` inside or immediately after the equation environment.
* Avoid using images for equations.
* Keep notation consistent across the paper.

Example:

```latex
\begin{equation}
\label{eq:threshold-shift}
\Delta \tau_i = \tau_i^{poisoned} - \tau_i^{clean}.
\end{equation}
```

---

## 17. Special Math Symbols Provided by `llncs`

The class provides extra math-mode commands.

Relational symbols:

| Command   | Meaning                               |
| --------- | ------------------------------------- |
| `\grole`  | Greater-over-less relation            |
| `\getsto` | Left/right arrow relation             |
| `\lid`    | Less-than-or-equal styled relation    |
| `\gid`    | Greater-than-or-equal styled relation |

Blackboard-style symbols are also provided as math-mode commands when AMS fonts are not used.

| Command   | Symbol intent      |
| --------- | ------------------ |
| `\bbbc`   | Complex numbers    |
| `\bbbf`   | Field-like F       |
| `\bbbh`   | H                  |
| `\bbbk`   | K                  |
| `\bbbm`   | M                  |
| `\bbbn`   | Natural numbers    |
| `\bbbp`   | P                  |
| `\bbbq`   | Rational numbers   |
| `\bbbr`   | Real numbers       |
| `\bbbs`   | S                  |
| `\bbbt`   | T                  |
| `\bbbz`   | Integers           |
| `\bbbone` | Indicator-like one |

Use these only in math mode.

Preferred modern approach: if allowed by the venue, load standard AMS packages for math symbols. If the venue restricts packages, use the LNCS-provided commands.

---

## 18. Theorem-Like Environments

The `llncs` class defines several theorem-like environments.

### 18.1 Italic Body, Bold Run-In Heading

Use these for formal mathematical statements:

```latex
\begin{theorem}
Statement of the theorem.
\end{theorem}

\begin{lemma}
Statement of the lemma.
\end{lemma}

\begin{corollary}
Statement of the corollary.
\end{corollary}

\begin{proposition}
Statement of the proposition.
\end{proposition}

\begin{definition}
Definition text.
\end{definition}
```

Available environments:

* `theorem`
* `lemma`
* `corollary`
* `proposition`
* `definition`

### 18.2 Roman Body, Bold Run-In Heading

Use these for examples, problems, notes, and related material:

```latex
\begin{example}
Example text.
\end{example}

\begin{remark}
Remark text.
\end{remark}
```

Available environments:

* `case`
* `conjecture`
* `example`
* `exercise`
* `note`
* `problem`
* `property`
* `question`
* `remark`
* `solution`

### 18.3 Unnumbered Claim and Proof

Use:

```latex
\begin{claim}
Claim text.
\end{claim}

\begin{proof}
Proof text.
\qed
\end{proof}
```

Rules:

* `claim` and `proof` are unnumbered.
* Proof headings are italic run-in headings.
* Use `\qed` before the end of a proof if you need the closing square.

---

## 19. Defining Custom Theorem Environments

Use `\spnewtheorem`, not the standard `\newtheorem`, when defining LNCS-style theorem environments.

Numbered environment sharing the theorem counter:

```latex
\spnewtheorem{maintheorem}[theorem]{Main Theorem}{\bfseries}{\itshape}
```

General syntax:

```latex
\spnewtheorem{<env_name>}[<num_like>]{<caption>}{<caption_font>}{<body_font>}
```

Example with a separate counter:

```latex
\spnewtheorem{assumption}{Assumption}{\bfseries}{\itshape}
```

Unnumbered custom environment:

```latex
\spnewtheorem*{observation}{Observation}{\bfseries}{\itshape}
```

Guidelines:

* Reuse existing environments when possible.
* Define custom environments only when they improve clarity.
* Keep theorem naming consistent across the paper.
* Avoid mixing many similar environment names such as `Observation`, `Note`, `Remark`, and `Claim` unless each has a clear role.

---

## 20. Credits, Acknowledgments, and Disclosure of Interests

Credits and acknowledgments belong at the end of the paper, immediately before the references.

Use the `credits` environment:

```latex
\begin{credits}
\subsubsection{\ackname}
This study was funded by X under grant number Y.

\subsubsection{\discintname}
The authors have no competing interests to declare that are relevant to the content of this article.
\end{credits}
```

Rules:

* The `credits` environment prints text and run-in headings in the expected small font size.
* `\ackname` generates the correct “Acknowledgments” heading.
* `\discintname` generates the correct “Disclosure of Interests” heading.
* Acknowledgments are optional.
* Disclosure of Interests is mandatory in the current template guidance.
* If there are no competing interests, explicitly state that there are none.
* If there are competing interests, declare them specifically and transparently.

Examples of disclosure statements:

```latex
\subsubsection{\discintname}
The authors have no competing interests to declare that are relevant to the content of this article.
```

```latex
\subsubsection{\discintname}
Author A has received research funding from Company X. Author B declares no competing interests.
```

---

## 21. Citations and References

LNCS supports three citation styles:

1. Numeric citations, for example `[1]`, `[3--5]`, `[4--6,9]`.
2. Label citations, for example `[CE1]`, `[AB1,XY2]`.
3. Author-year citations, for example `(Smith et al. 2000)`.

Preferred style:

* Use numeric citations unless the venue explicitly requests another style.
* Use square brackets for numeric references.
* Group multiple citations when appropriate.

Examples:

```latex
This problem has been studied in prior work~\cite{ref_article1}.
Several related approaches exist~\cite{ref_article1,ref_lncs1,ref_book1}.
```

---

## 22. BibTeX Bibliography

Use the provided Springer bibliography style:

```latex
\bibliographystyle{splncs04}
\bibliography{references}
```

Rules:

* Keep `splncs04.bst` in the project directory or install it in your TeX tree.
* Store bibliography entries in a `.bib` file, for example `references.bib`.
* Put DOIs in the `doi` field.
* Let BibTeX format DOI links automatically.

Example `.bib` entry:

```bibtex
@article{author2016example,
  author  = {Author, First},
  title   = {Article Title},
  journal = {Journal Name},
  volume  = {2},
  number  = {5},
  pages   = {99--110},
  year    = {2016},
  doi     = {10.1000/exampledoi}
}
```

Recommended compile sequence when using BibTeX:

```bash
latex main
bibtex main
latex main
latex main
```

Or with PDF output, depending on your figure formats and toolchain:

```bash
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

---

## 23. Manual Bibliography

If you do not use BibTeX, use `thebibliography`:

```latex
\begin{thebibliography}{8}

\bibitem{ref_article1}
Author, F.: Article title. Journal \textbf{2}(5), 99--110 (2016)

\bibitem{ref_lncs1}
Author, F., Author, S.: Title of a proceedings paper. In: Editor, F., Editor, S. (eds.)
CONFERENCE 2016, LNCS, vol. 9999, pp. 1--13. Springer, Heidelberg (2016).
\doi{10.1000/exampledoi}

\end{thebibliography}
```

Manual bibliography rules:

* Use consistent formatting.
* Include all required metadata: authors, title, venue, volume, pages, publisher, year, and DOI where available.
* Use `\doi{...}` for DOI values.
* Do not manually write `https://doi.org/...`; the class expands DOI values appropriately.

---

## 24. DOI Rules

With BibTeX:

```bibtex
doi = {10.1000/exampledoi}
```

Without BibTeX:

```latex
\doi{10.1000/exampledoi}
```

Rules:

* Provide the DOI without the `https://doi.org/` prefix.
* Do not add final punctuation inside the DOI command.
* Check that underscores and special characters compile correctly.

---

## 25. URLs and Hyperlinks

The sample template gives optional formatting for URL appearance when using hyperlink-related packages:

```latex
% \usepackage{color}
% \renewcommand\UrlFont{\color{blue}\rmfamily}
% \urlstyle{rm}
```

Guidelines:

* Use `\url{...}` for URLs.
* Keep URL formatting consistent with Springer style.
* Avoid raw long URLs in the text body when a citation is more appropriate.
* For homepages in references, include access dates when required.

Example reference:

```latex
\bibitem{ref_url1}
LNCS Homepage, \url{http://www.springer.com/lncs}, last accessed 2023/10/25
```

---

## 26. Figures, Tables, and Cross-References

Always use labels and cross-references.

Recommended label prefixes:

```latex
\label{sec:introduction}
\label{fig:architecture}
\label{tab:results}
\label{eq:objective}
\label{thm:main}
```

Recommended references:

```latex
Section~\ref{sec:method}
Fig.~\ref{fig:architecture}
Table~\ref{tab:results}
Eq.~\ref{eq:objective}
Theorem~\ref{thm:main}
```

Rules:

* Use `~` between the reference name and number to avoid line breaks.
* Do not write hardcoded numbers such as “Figure 3” manually.
* Make sure every figure and table is referenced in the text.
* Make sure labels are unique.

---

## 27. Recommended Full Paper Skeleton

```latex
\documentclass[runningheads]{llncs}

\usepackage[T1]{fontenc}
\usepackage{graphicx}

\begin{document}

\title{Contribution Title}
\titlerunning{Short Title}

\author{
First Author\inst{1}\orcidID{0000-1111-2222-3333}
\and
Second Author\inst{2}\orcidID{1111-2222-3333-4444}
}

\authorrunning{F. Author et al.}

\institute{
Institution One, City, Country\\
\email{first@example.com}
\and
Institution Two, City, Country\\
\email{second@example.com}
}

\maketitle

\begin{abstract}
Write a 150--250 word summary of the problem, method, results, and conclusion.

\keywords{Keyword One \and Keyword Two \and Keyword Three}
\end{abstract}

\section{Introduction}
Explain the problem, motivation, gap, contribution, and paper organization.

\section{Related Work}
Discuss directly relevant prior work and position your contribution.

\section{Method}
Describe the proposed method with enough detail for reproducibility.

\section{Experimental Setup}
Describe datasets, baselines, metrics, parameters, and evaluation protocol.

\section{Results}
Present the main results using tables and figures.

\section{Discussion}
Explain interpretation, limitations, threats to validity, and practical implications.

\section{Conclusion}
Summarize the contribution and main findings without introducing new results.

\begin{credits}
\subsubsection{\ackname}
Optional acknowledgments.

\subsubsection{\discintname}
The authors have no competing interests to declare that are relevant to the content of this article.
\end{credits}

\bibliographystyle{splncs04}
\bibliography{references}

\end{document}
```

---

## 28. Common Mistakes to Avoid

### 28.1 Layout Mistakes

Avoid:

* Changing margins.
* Reducing line spacing.
* Using negative vertical spacing to fit content.
* Shrinking tables or figures until unreadable.
* Manually forcing page breaks everywhere.
* Using custom heading styles that override LNCS formatting.

### 28.2 Header Mistakes

Avoid:

* Forgetting `\maketitle`.
* Putting emails in `\author`.
* Using commas instead of `\and` between authors.
* Using `\thanks` in `\author` or `\institute`.
* Forgetting `\titlerunning` when the title is too long.
* Forgetting `\authorrunning` when the author list is too long.

### 28.3 Abstract and Keyword Mistakes

Avoid:

* Abstract shorter than 150 words or much longer than 250 words.
* Keywords outside the abstract environment.
* Separating keywords with commas instead of `\and`.
* Lowercase keyword starts when title case is expected.

### 28.4 Figure and Table Mistakes

Avoid:

* Figure captions above figures.
* Table captions below tables.
* Missing labels.
* Labels before captions.
* Referencing figures or tables by hardcoded numbers.
* Using screenshots for plots or tables.
* Using low-resolution raster images for line art.

### 28.5 Reference Mistakes

Avoid:

* Using a bibliography style other than `splncs04` unless required.
* Missing DOI fields.
* Inconsistent author initials.
* Manually formatting DOI URLs incorrectly.
* Uncited bibliography entries.
* Citations missing from the bibliography.

### 28.6 Disclosure Mistakes

Avoid:

* Omitting the Disclosure of Interests statement.
* Placing acknowledgments after references.
* Writing an ambiguous disclosure such as `None` without context.

Use a complete sentence:

```latex
The authors have no competing interests to declare that are relevant to the content of this article.
```

---

## 29. Pre-Submission Checklist

### Files

* [ ] `main.tex` compiles successfully.
* [ ] `llncs.cls` is available locally or through the TeX installation.
* [ ] `splncs04.bst` is available if using BibTeX.
* [ ] All figure files are included.
* [ ] The `.bib` file is included if using BibTeX.

### Preamble

* [ ] The document uses `\documentclass[runningheads]{llncs}` or another accepted `llncs` setup.
* [ ] `\usepackage[T1]{fontenc}` is present.
* [ ] `\usepackage{graphicx}` is present if figures are used.
* [ ] No manual margin or line-spacing changes are present.

### Header

* [ ] Title is correctly capitalized.
* [ ] Title has no final punctuation.
* [ ] Long title has `\titlerunning{...}`.
* [ ] Authors are separated with `\and`.
* [ ] Affiliations use `\inst{...}` consistently.
* [ ] ORCID IDs are included where available.
* [ ] Long author list has `\authorrunning{...}`.
* [ ] Emails are placed in `\institute`, not `\author`.
* [ ] `\maketitle` is present.

### Abstract and Keywords

* [ ] Abstract is approximately 150--250 words.
* [ ] Abstract states problem, method, result, and implication.
* [ ] Keywords are inside the abstract environment.
* [ ] Keywords are separated using `\and`.
* [ ] Keywords start with capital letters.

### Body

* [ ] Heading hierarchy is clean and has no more than four levels.
* [ ] Only necessary equations are numbered.
* [ ] Every figure is referenced in the text.
* [ ] Every table is referenced in the text.
* [ ] Table captions are above tables.
* [ ] Figure captions are below figures.
* [ ] Labels are unique and placed after captions.
* [ ] Figures are readable at final size.
* [ ] Vector graphics are used for diagrams and plots where possible.

### Credits

* [ ] `credits` environment appears before references.
* [ ] Acknowledgments are included if needed using `\ackname`.
* [ ] Disclosure of Interests is included using `\discintname`.
* [ ] Competing interests are explicitly declared, even if there are none.

### References

* [ ] Numeric citation style is used unless another style is required.
* [ ] `\bibliographystyle{splncs04}` is used with BibTeX.
* [ ] DOI fields are included where available.
* [ ] All citations resolve correctly.
* [ ] No `??` references remain in the PDF.
* [ ] No undefined citation warnings remain.

### Final PDF

* [ ] The PDF compiles without errors.
* [ ] No overfull boxes remain in important visible content.
* [ ] No missing characters or broken accented names appear.
* [ ] Running heads are not too long.
* [ ] Figures and tables do not overflow the text area.
* [ ] The final PDF visually follows LNCS style.

---

## 30. Minimal Compliance Checklist

For a quick final audit, verify at least these points:

* [ ] Uses `llncs` class.
* [ ] Uses T1 font encoding.
* [ ] Does not manually alter margins or spacing.
* [ ] Has title, authors, affiliations, abstract, and keywords.
* [ ] Calls `\maketitle`.
* [ ] Has 150--250 word abstract.
* [ ] Uses `\and` for authors and keywords.
* [ ] Places table captions above tables.
* [ ] Places figure captions below figures.
* [ ] Uses vector figures when possible.
* [ ] Uses `splncs04` for BibTeX references.
* [ ] Includes mandatory Disclosure of Interests.
* [ ] Compiles cleanly with all references resolved.

---

## 31. Recommended Agent/Author Instruction

Use this instruction when asking an editor, coauthor, or coding agent to convert a paper into LNCS format:

```text
Convert the paper to Springer LNCS LaTeX format using the provided llncs.cls and splncs04.bst files. Preserve the scientific content. Do not change margins, spacing, heading styles, or bibliography style manually. Use \documentclass[runningheads]{llncs}, T1 font encoding, graphicx for figures, \maketitle, a 150--250 word abstract, keywords inside the abstract separated by \and, author affiliations with \inst, ORCID IDs where available, table captions above tables, figure captions below figures, and BibTeX style splncs04. Add a credits environment before references with optional acknowledgments and a mandatory Disclosure of Interests statement. Compile until all references, citations, running heads, figures, and tables are resolved cleanly.
```
