from database import RefereeDbCockroach


'''
Test the new cockroachdb implementation
'''

if __name__ == "__main__":

    mentorLength = None
    db = RefereeDbCockroach()
    x = db.getMentors()
    mentorLength = len(x)
    assert mentorLength > 0
    print(x)

    refereeLength = None
    x = db.getReferees()
    refereeLength = len(x)
    assert refereeLength > 0
    print(x)

    x = db.refExists('curby', 'kate')
    assert x == True

    x = db.findReferee('curby', 'kate')
    assert len(x) == 4
    print(x)

    x = db.mentorExists('kate','curby')
    assert x == False

    x = db.mentorExists('david', 'helfgott')
    assert x == True

    x = db.findMentor('martin', 'cooley')
    assert len(x) == 3
    print(x)

    db.addMentor('asdf', 'qwer')
    x = db.getMentors()
    assert len(x) == mentorLength + 1

    db.addReferee('qwer', 'asdf', 9999)
    x = db.getReferees()
    assert len(x) == refereeLength + 1

    '''
        def getMentoringSessions(self) -> dict:
        def addMentorSession(self,
    '''
    print ('Tests Complete!!!')
