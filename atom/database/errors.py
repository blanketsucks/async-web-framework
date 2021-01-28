class DatabaseError(Exception):
    pass

class NoConnections(DatabaseError):
    pass