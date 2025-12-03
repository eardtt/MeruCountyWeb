import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone # <-- NEW IMPORT
from league.models import Team, Match

class Command(BaseCommand):
    help = 'Generates a full league schedule by saving each match individually and using timezone-aware dates.'

    def handle(self, *args, **options):
        date_format = '%Y-%m-%d'
        
        # --- Start Date Hardcoded and Made Timezone-Aware ---
        start_date_naive = datetime.datetime.combine(
            datetime.date.today() + datetime.timedelta(days=1), 
            datetime.time(0, 0) # Set time to midnight
        )
        # Make the starting datetime object timezone-aware
        start_date = timezone.make_aware(start_date_naive)
        
        days_between_weeks = 7 
        
        self.stdout.write(self.style.NOTICE("--- Starting Individual Fixture Generation (Timezone Aware) ---"))
        self.stdout.write(self.style.SUCCESS(f"Start Date set to: {start_date.strftime(date_format)} (Timezone Aware)"))
        self.stdout.write(self.style.SUCCESS(f"Match days separated by: {days_between_weeks} days"))

        all_teams = list(Team.objects.all().order_by('pk'))
        num_actual_teams = len(all_teams)

        if num_actual_teams < 2:
            raise CommandError('Need at least 2 teams to generate a schedule.')

        all_matches_to_save = [] # List to hold both home and away match objects
        
        # --- Round-Robin Setup ---
        
        if num_actual_teams % 2 != 0:
            teams = all_teams + [None]
        else:
            teams = all_teams
        
        num_teams = len(teams)
        total_rounds = num_teams - 1 

        if Match.objects.exists():
            self.stdout.write(self.style.WARNING(
                'WARNING: Existing matches found. Generated fixtures will be added to the schedule.'
            ))

        # --- PHASE 1: Generate First Leg Fixtures (Home Matches) ---
        self.stdout.write(self.style.SUCCESS(f'--- Generating First Leg Fixtures for {num_actual_teams} Teams ---'))

        current_datetime = start_date # Use current_datetime for timezone-aware date

        for round_num in range(total_rounds):
            if round_num > 0:
                current_datetime += datetime.timedelta(days=days_between_weeks)
                
            self.stdout.write(f'--- Round {round_num + 1} (Date: {current_datetime.strftime(date_format)}) ---')
            
            half_size = num_teams // 2

            for i in range(half_size):
                team1 = teams[i]
                team2 = teams[i + half_size]
                
                if team1 and team2:
                    # Leg 1 (Home)
                    match_home = Match(
                        home_team=team1,
                        away_team=team2,
                        match_date=current_datetime, # Use the timezone-aware date
                        is_played=False
                    )
                    all_matches_to_save.append(match_home)
                    self.stdout.write(f'  - {team1.name} vs {team2.name}')

            teams.insert(1, teams.pop())
        
        # --- PHASE 2: Generate Second Leg Fixtures (Away Matches) ---
        
        leg1_matches_copy = all_matches_to_save[:]
        
        if num_actual_teams > 2:
            self.stdout.write(self.style.SUCCESS('\n--- Generating Second Leg (Return) Fixtures ---'))
            for match in leg1_matches_copy:
                # Calculate return date based on original date
                return_datetime = match.match_date + datetime.timedelta(days=(total_rounds * days_between_weeks))

                match_away = Match(
                    home_team=match.away_team,
                    away_team=match.home_team,
                    match_date=return_datetime, # Use the calculated timezone-aware date
                    is_played=False
                )
                all_matches_to_save.append(match_away)
                self.stdout.write(f'  - {match_away.home_team.name} vs {match_away.away_team.name} (Return Leg)')


        # --- PHASE 3: Commit Matches Individually (The Critical Fix) ---
        total_matches = len(all_matches_to_save)
        self.stdout.write(self.style.NOTICE(f'\n--- Committing {total_matches} matches to database... ---'))

        count = 0
        try:
            for match in all_matches_to_save:
                match.save()
                count += 1
                if count % 10 == 0:
                    self.stdout.write(f'Progress: {count}/{total_matches} saved.')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nCRITICAL SAVE ERROR: {e}"))
            connection.close()
            return

        connection.close() 

        self.stdout.write(self.style.SUCCESS(
            f'\nSuccessfully created {count} total fixtures and closed DB connection! Script should now exit.'
        ))