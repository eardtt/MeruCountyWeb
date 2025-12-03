from django.contrib import admin
from django.db.models import Sum, F
# Ensure all models are imported, including Goal and Card
from .models import Team, Player, Match, Referee, MatchReport, Goal, Card

# ----------------- INLINE ADMINS (FIXED) -----------------
# These will be embedded directly into the MatchAdmin form

class GoalInline(admin.TabularInline):
    model = Goal
    extra = 1
    # FIX: Changed 'player' to 'scorer' to match the model field name
    fields = ('scorer', 'team', 'minute') 

class CardInline(admin.TabularInline):
    model = Card
    extra = 1
    # FIX: The field for the player who received the card is likely named 
    # 'player' in the Card model, as it was not renamed in the migration. 
    # Assuming 'player' is correct for Card.
    fields = ('player', 'card_type', 'minute', 'reason')

class MatchReportInline(admin.StackedInline):
    model = MatchReport
    can_delete = False
    verbose_name_plural = 'Match Report'
    fields = ('general_report', 'referee_rating', 'is_verified')

# ----------------- MODEL ADMINS -----------------

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'match_date', 'referee', 'is_played', 'home_score', 'away_score', 'get_winner')
    list_filter = ('is_played', 'match_date', 'referee', 'home_team', 'away_team')
    search_fields = ('home_team__name', 'away_team__name', 'referee__name')
    date_hierarchy = 'match_date'

    # Embed the event tracking models and report into the Match form
    inlines = [GoalInline, CardInline, MatchReportInline]
    
    # Organize the fields on the Match change form
    fieldsets = (
        (None, {
            'fields': ('home_team', 'away_team', 'referee', 'match_date', 'venue', 'is_played')
        }),
        ('Final Score (Calculated from Goals Below)', {
            # These fields are read-only and will be updated in save_model
            'fields': ('home_score', 'away_score'),
            'classes': ('collapse',), # Hide by default
        }),
    )
    
    # Make score fields read-only so they are calculated, not manually entered
    readonly_fields = ('home_score', 'away_score',)


    def save_model(self, request, obj, form, change):
        """
        Overrides save_model to automatically calculate home_score and away_score 
        from the Goals entered in the inline forms before saving the Match object.
        """
        # Save the Match object first (needed for related Goal objects)
        super().save_model(request, obj, form, change)
        
        # Recalculate scores based on the Goals related to this match object
        
        # Calculate Home Score
        home_goals = obj.goals.filter(team=obj.home_team).count()
        
        # Calculate Away Score
        away_goals = obj.goals.filter(team=obj.away_team).count()

        # Update the Match object's score fields
        if obj.home_score != home_goals or obj.away_score != away_goals:
            obj.home_score = home_goals
            obj.away_score = away_goals
            
            # Save the object again with the updated scores, bypassing save_model recursion
            Match.objects.filter(pk=obj.pk).update(
                home_score=home_goals, 
                away_score=away_goals
            )


# --- Registration for Other Models ---

admin.site.register(Referee)
admin.site.register(Team)
admin.site.register(Player)