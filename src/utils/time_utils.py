from datetime import datetime
from typing import List

def get_past_school_year_prefixes(start_year: int = 2026, current_date: datetime = None) -> List[str]:
    """
    Génère la liste exhaustive des préfixes de toutes les années scolaires passées 
    jusqu'à l'année active, afin de pouvoir les exclure des recherches.
    
    Args:
        start_year (int): L'année de départ théorique des archives sur le Drive.
        current_date (datetime, optional): La date de référence.
        
    Returns:
        List[str]: Une liste de préfixes (ex: ['R25_', 'R26_', ..., 'R28_']).
    """
    if current_date is None:
        current_date = datetime.now()
        
    active_year = current_date.year
    if current_date.month < 8:
        active_year -= 1
        
    past_prefixes = []
    # On boucle depuis l'année de départ jusqu'à l'année active (exclue)
    for y in range(start_year, active_year):
        short_year = str(y)[-2:]
        past_prefixes.append(f"R{short_year}_")
        
    return past_prefixes