# JmeterToConfluence

Markdown
# JMeter to Confluence Report Generator

Script Python pentru automatizarea parsarii rapoartelor de performanta JMeter (HTML Dashboard) si publicarea acestora in Atlassian Confluence. Genereaza o pagina structurata cu sumar executiv, tabele de performanta si grafice interactive.

## Cerinte preliminare

1. Python 3.x
2. Instalarea pachetelor necesare:

```bash
pip install -r requirements.txt
(Pachetele incluse: requests, beautifulsoup4, lxml)

Configurare
Inainte de a rula scriptul, editati sectiunea de configurare de la inceputul fisierului jmeterToConfluence.py:

EMAIL: Adresa de email asociata contului Atlassian.

API_TOKEN: Tokenul generat din setarile de securitate Atlassian.

PAGE_ID: ID-ul paginii Confluence pe care doriti sa o suprascrieti/actualizati.

DOMAIN: Numele domeniului companiei in Confluence (ex: fintechos).

Mod de utilizare
Rulati scriptul din linia de comanda, indicand calea catre folderul raportului JMeter si adresa serverului local.

Bash
python jmeterToConfluence.py [CALE_FOLDER_JMETER] [URL_SERVER_LOCAL]
Exemplu de executie:

Bash
python jmeterToConfluence.py ./C_01_ProductFactory_Insurance_V2451 http://localhost:8000
Daca nu specificati argumente, scriptul va rula implicit pe folderul curent (.) utilizand adresa http://localhost:8000.

Functionalitati principale
Grafice interactive prin Iframe: Integreaza nativ chart-urile din JMeter in pagina de Confluence pastrand interactivitatea completa (zoom, hover, tooltips) folosind macro-uri validate Atlassian (Resource Identifier).

Parsare dinamica DFS: Navigheaza algoritmic structura de meniu JMeter (index.html) pentru a identifica si extrage automat graficele, indiferent de numarul acestora sau de denumirile viitoarelor teste.

Integrare date statistice: Citeste si proceseaza fisierul statistics.json pentru a popula tabelele de performanta si sectiunea de key findings cu metrici exacte (TPS, timpi de raspuns, erori) fara a depinde de date hardcodate.

Patch de retea integrat: Repara automat dependintele locale de Bootstrap corupte de limitarile sistemului de operare (Filename too long), folosind un CDN public pentru a asigura incarcarea corecta a scripturilor JS in interiorul iframe-urilor.

Standardizare design Confluence: Aplica un layout tabelar curat (design oficial Atlassian) si limiteaza automat vizibilitatea graficelor in macro-ul de cuprins (TOC - maxLevel 2) pentru a mentine o documentatie usor de citit.
