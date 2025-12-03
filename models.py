from django.db import models
from django.db.models import Q, F
from django.utils.text import slugify
from django.utils import timezone
import datetime # Kept for datetime manipulation

# --- Team Standings Manager (Required for Standings View) ---
class TeamStandingsManager(models.Manager):
    def get_standings(self):
        teams = self.get_queryset().all()
        standings = []
        for team in teams:
            played_home = Match.objects.filter(home_team=team, is_played=True)
            played_away = Match.objects.filter(away_team=team, is_played=True)
            all_played = played_home | played_away 
            stats = {
                'team': team, 'P': all_played.count(),
                'W': 0, 'D': 0, 'L': 0,
                'GF': 0, 'GA': 0, 'GD': 0, 'Pts': 0
            }
            for match in all_played:
                if match.home_team == team:
                    gf, ga = match.home_score, match.away_score
                else: 
                    gf, ga = match.away_score, match.home_score
                stats['GF'] += gf
                stats['GA'] += ga
                if gf > ga:
                    stats['W'], stats['Pts'] = stats['W'] + 1, stats['Pts'] + 3
                elif gf == ga:
                    stats['D'], stats['Pts'] = stats['D'] + 1, stats['Pts'] + 1
                else:
                    stats['L'] += 1
            stats['GD'] = stats['GF'] - stats['GA']
            standings.append(stats)
        standings.sort(
            key=lambda x: (x['Pts'], x['GD'], x['GF']), reverse=True
        )
        return standings

# ----------------------------------------------------
# --- CORE MODELS (ADDED MISSING FIELDS) ---
# ----------------------------------------------------

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    
    objects = models.Manager() 
    standings_manager = TeamStandingsManager() 

    # Stats fields for compatibility with your previous admin/views (can be hidden in admin)
    matches_played = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    goals_for = models.IntegerField(default=0)
    goals_against = models.IntegerField(default=0)
    goal_difference = models.IntegerField(default=0)
    points = models.IntegerField(default=0)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Referee(models.Model):
    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)

    def __str__(self):
        return self.name

class Match(models.Model):
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    match_date = models.DateTimeField(default=timezone.now) 
    
    # --- FIELD ADDED FOR ADMIN COMPATIBILITY ---
    venue = models.CharField(max_length=100, blank=True, null=True, help_text="Location where the match was played.")
    
    home_score = models.IntegerField(default=0)
    away_score = models.IntegerField(default=0)
    is_played = models.BooleanField(default=False)
    referee = models.ForeignKey(Referee, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['match_date']
        verbose_name_plural = "Matches"

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} ({self.match_date.strftime('%Y-%m-%d')})"

    def save(self, *args, **kwargs):
        if self.home_score > 0 or self.away_score > 0:
            self.is_played = True
        else:
            self.is_played = False
        super().save(*args, **kwargs)

    def get_winner(self):
        if not self.is_played:
            return "N/A"
        if self.home_score > self.away_score:
            return self.home_team.name
        elif self.away_score > self.home_score:
            return self.away_team.name
        else:
            return "Draw"
    get_winner.short_description = 'Winner' 


class Player(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    jersey_number = models.IntegerField(unique=True)
    id_number = models.CharField(max_length=20, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.team.name})"

class Goal(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='goals')
    scorer = models.ForeignKey(Player, on_delete=models.CASCADE)
    
    # --- FIELDS ADDED FOR ADMIN COMPATIBILITY ---
    team = models.ForeignKey(Team, on_delete=models.CASCADE, help_text="Team that scored the goal.") # Used in save_model logic
    minute = models.IntegerField(verbose_name='Time (min)', help_text="Time of the goal (1-90+).")
    
    def __str__(self):
        return f"Goal by {self.scorer.name} in match {self.match}"

class Card(models.Model):
    CARD_TYPES = [
        ('Y', 'Yellow Card'),
        ('R', 'Red Card'),
        ('2Y', 'Second Yellow/Red')
    ]
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    card_type = models.CharField(max_length=2, choices=CARD_TYPES)
    
    # --- FIELDS ADDED FOR ADMIN COMPATIBILITY ---
    minute = models.IntegerField(verbose_name='Time (min)', help_text="Time the card was given (1-90+).")
    reason = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"{self.get_card_type_display()} for {self.player.name} in match {self.match}"

class MatchReport(models.Model):
    match = models.OneToOneField(Match, on_delete=models.CASCADE)
    
    # --- FIELDS ADDED FOR ADMIN COMPATIBILITY ---
    general_report = models.TextField(blank=True, null=True)
    referee_rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 11)], default=5) # 1-10 rating
    
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Report for {self.match}"