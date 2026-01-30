"""
Web Search Tool - Pesquisa na Internet com DuckDuckGo
Respeita a privacidade do utilizador
"""

import json
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    """Extrai texto de HTML."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {'script', 'style', 'head', 'meta', 'link'}
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag

    def handle_endtag(self, tag):
        self.current_tag = None

    def handle_data(self, data):
        if self.current_tag not in self.skip_tags:
            text = data.strip()
            if text:
                self.text_parts.append(text)

    def get_text(self) -> str:
        return ' '.join(self.text_parts)


class WebSearchTool:
    """
    Ferramenta de pesquisa na web usando DuckDuckGo.
    Não requer API key e respeita privacidade.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_results = config.get("max_results", 5)
        self.timeout = config.get("timeout", 10)

    def search(self, query: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Pesquisa na web usando DuckDuckGo.

        Args:
            query: Termo de pesquisa
            max_results: Número máximo de resultados

        Returns:
            Lista de resultados com título, URL e descrição
        """
        max_results = max_results or self.max_results
        results = []

        try:
            # Try using duckduckgo-search library first
            try:
                from duckduckgo_search import DDGS

                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=max_results):
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "description": r.get("body", "")
                        })
                return results

            except ImportError:
                # Fallback to manual HTML parsing
                pass

            # Fallback: Use DuckDuckGo HTML version
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            request = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0'
                }
            )

            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                html = response.read().decode('utf-8')

            # Parse results (simplified)
            results = self._parse_ddg_html(html, max_results)

        except Exception as e:
            results.append({
                "error": f"Erro na pesquisa: {str(e)}",
                "title": "Erro",
                "url": "",
                "description": str(e)
            })

        return results

    def _parse_ddg_html(self, html: str, max_results: int) -> List[Dict[str, Any]]:
        """Parse DuckDuckGo HTML results."""
        results = []

        # Simple regex-based parsing for DuckDuckGo HTML
        import re

        # Find result blocks
        result_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
        snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>([^<]*)</a>'

        links = re.findall(result_pattern, html)
        snippets = re.findall(snippet_pattern, html)

        for i, (url, title) in enumerate(links[:max_results]):
            description = snippets[i] if i < len(snippets) else ""

            # Decode URL if needed
            if url.startswith("//duckduckgo.com/l/?uddg="):
                url_match = re.search(r'uddg=([^&]+)', url)
                if url_match:
                    url = urllib.parse.unquote(url_match.group(1))

            results.append({
                "title": title.strip(),
                "url": url,
                "description": description.strip()
            })

        return results

    def fetch_page(self, url: str, max_length: int = 5000) -> Dict[str, Any]:
        """
        Obtém o conteúdo de uma página web.

        Args:
            url: URL da página
            max_length: Tamanho máximo do texto extraído

        Returns:
            Conteúdo da página
        """
        try:
            request = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0'
                }
            )

            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                html = response.read().decode('utf-8', errors='ignore')

            # Extract text from HTML
            extractor = HTMLTextExtractor()
            extractor.feed(html)
            text = extractor.get_text()

            # Truncate if necessary
            if len(text) > max_length:
                text = text[:max_length] + "..."

            return {
                "url": url,
                "content": text,
                "truncated": len(text) > max_length
            }

        except Exception as e:
            return {
                "url": url,
                "error": str(e)
            }

    def search_news(self, query: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Pesquisa notícias recentes.

        Args:
            query: Termo de pesquisa
            max_results: Número máximo de resultados

        Returns:
            Lista de notícias
        """
        try:
            from duckduckgo_search import DDGS

            max_results = max_results or self.max_results
            results = []

            with DDGS() as ddgs:
                for r in ddgs.news(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "description": r.get("body", ""),
                        "source": r.get("source", ""),
                        "date": r.get("date", "")
                    })

            return results

        except ImportError:
            return [{"error": "duckduckgo-search não instalado. Use: pip install duckduckgo-search"}]
        except Exception as e:
            return [{"error": str(e)}]


# Wrapper function for agent tool interface
def web_search(query: str) -> str:
    """
    Interface simplificada para pesquisa web.
    Usada pelo agente.
    """
    tool = WebSearchTool({"max_results": 5})
    results = tool.search(query)

    if not results:
        return "Nenhum resultado encontrado."

    output = [f"Resultados para: '{query}'\n"]

    for i, r in enumerate(results, 1):
        if "error" in r:
            output.append(f"  ⚠️ {r['error']}")
        else:
            output.append(f"  {i}. {r['title']}")
            output.append(f"     🔗 {r['url']}")
            if r.get('description'):
                desc = r['description'][:150] + "..." if len(r['description']) > 150 else r['description']
                output.append(f"     {desc}")
            output.append("")

    return "\n".join(output)
