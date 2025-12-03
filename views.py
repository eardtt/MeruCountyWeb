from django.shortcuts import render, get_object_or_404
from django.db import transaction
from django.db.models import Count, F, Q
from .models import Team, Match, Player # Ensure all models are imported

# --- STANDINGS VIEW ---
def standings(request):
    """
    Retrieves the league standings and top scorers.
    """
    final_standings = Team.standings_manager.get_standings()
    
    scorers = Player.objects.annotate(
        goals_count=Count('goal') 
    ).filter(
        goals_count__gt=0
    ).order_by(
        '-goals_count', 
        'name'
    )[:10]

    context = {
        'title': 'League Standings',
        'standings_list': final_standings, 
        'scorers': scorers, 
    }
    return render(request, 'league/standings.html', context)


# --- SCHEDULE VIEW (UPDATED to show all matches) ---
def schedule(request):
    """Displays a list of all matches, separated into Played and Upcoming."""
    
    # Fetch ALL matches ordered by date
    all_matches = Match.objects.all().order_by('match_date')
    
    # Separate the list into two for display in the template
    played_matches = all_matches.filter(is_played=True)
    upcoming_matches = all_matches.filter(is_played=False)
    
    context = {
        # Both lists are now passed to the template
        'played_matches': played_matches,
        'upcoming_matches': upcoming_matches,
        'page_title': 'Match Schedule and Results'
    }
    return render(request, 'league/schedule.html', context)

# --- NEW TEAM LIST VIEW ---
def team_list(request):
    """Displays a list of all registered teams."""
    all_teams = Team.objects.all().order_by('name')
    
    context = {
        'title': 'All Teams in the League',
        'teams': all_teams,
    }
    return render(request, 'league/team_list.html', context)


# --- ROSTER VIEW ---
def roster(request, team_slug):
    """
    Displays the roster and statistics for a single team.
    """
    team = get_object_or_404(Team, slug=team_slug)
    
    # --- STATS AGGREGATION ---
    players = team.player_set.annotate(
        total_goals=Count('goal'),
        yellow_cards=Count(
            'card', 
            filter=Q(card__card_type='Y')
        ),
        red_cards=Count(
            'card', 
            filter=Q(card__card_type__in=['R', '2Y'])
        )
        
    ).order_by('jersey_number')

    context = {
        'title': f'{team.name} Roster',
        'team': team,
        'players': players,
    }
    return render(request, 'league/roster.html', context)


# --- MATCH DETAIL VIEW (CORRECTED FieldError) ---
def match_detail(request, match_pk):
    """
    Displays details, goals, and cards for a single match.
    """
    # Pre-fetch the related match objects
    match = get_object_or_404(
        Match.objects.select_related('home_team', 'away_team', 'referee', 'matchreport')
                     .prefetch_related('goals', 'card_set'), 
        pk=match_pk
    ) 
    
    # Separate goals for each team
    home_goals = match.goals.filter(team=match.home_team).order_by('minute')
    away_goals = match.goals.filter(team=match.away_team).order_by('minute')
    
    # FIX: Use 'player__team' in select_related to efficiently fetch the team 
    # through the player, since 'team' is not a direct FK on the Card model.
    all_cards = match.card_set.select_related('player__team').order_by('minute')

    context = {
        'title': f'{match.home_team.name} vs {match.away_team.name}',
        'match': match,
        'home_goals': home_goals,
        'away_goals': away_goals,
        'all_cards': all_cards,
    }
    return render(request, 'league/match_detail.html', context)