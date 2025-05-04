import requests
from bs4 import BeautifulSoup

API_KEY = "cbb9aaa8eda46eefad95434407bf40cc"  # Your ScraperAPI key

def scrape_google(query):  # ✅ Renamed from get_google_results
    query = query.replace(" ", "+")
    google_url = f"https://www.google.com/search?q={query}"
    scraperapi_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={google_url}"

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(scraperapi_url, headers=headers)

    if response.status_code != 200:
        return [{"title": "Error", "link": "", "snippet": f"Request failed with status code {response.status_code}"}]

    soup = BeautifulSoup(response.text, "html.parser")

    results = []
    for g in soup.find_all('div', class_='tF2Cxc'):
        title_elem = g.find('h3')
        link_elem = g.find('a')
        snippet_elem = g.find('span', class_='aCOpRe')

        if title_elem and link_elem:
            title = title_elem.text.strip()
            link = link_elem['href']
            snippet = snippet_elem.text.strip() if snippet_elem else "No description"
            results.append({
                "title": title,
                "link": link,
                "snippet": snippet
            })

    return results

# Test block
if __name__ == "__main__":
    search_query = "FAANG interview questions"
    results = scrape_google(search_query)  # ✅ Updated call here

    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}\n   {result['link']}\n   {result['snippet']}\n")
