from openstv.ballots import Ballots
from openstv.MethodPlugins.Condorcet import Condorcet
from itertools import chain

def flatten(listOfLists):
    "Flatten one level of nesting"
    return chain.from_iterable(listOfLists)

def iterate_rankings(names, votes, withdrawn_names):
        "Determine at least one winner"

        # If there's only one candidate left, return it
        if len(names) - len(withdrawn_names) == 1:
                return set(names) - set(withdrawn_names)

        ballots = Ballots()
        ballots.setAllNames(names)
        withdrawn_indices = [names.index(name) for name in withdrawn_names]
        ballots.setWithdrawn(withdrawn_indices)
        for ranking in votes:
                ballots.appendBallot(ranking)
        election = Condorcet(ballots)
        election.run()
        winning_names = [ballots.names[winner] for winner in election.winners]
        return winning_names

def coalesce_rankings(rankings):
        "Given a list of rankings, determine a ranking that best represents them."

        # If there's only one voter, there's no need to run an election
        if len(rankings) == 1:
                return rankings[0]

        names = list(set(flatten(rankings)))
        votes = [[names.index(name) for name in ranking] for ranking in rankings]
        winners = []
        while len(winners) < len(names):
                winners += iterate_rankings(names, votes, winners)
        return winners

if __name__ == "__main__":
        rankings = [
                ['one','two','three'],
                ['two','one','three'],
                ['two','three','one'],
        ]

        print coalesce_rankings(rankings)

