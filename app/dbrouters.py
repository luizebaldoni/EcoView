class MonitoringRouter:
    """DB router to send monitoring app models to specific databases.

    - Models named 'BriseSensorReading' -> database 'brise'
    - Models named 'PavimentosSensorReading' -> database 'pavimentos'
    - Other models -> 'default'
    """

    def db_for_read(self, model, **hints):
        name = model.__name__
        if name == 'BriseSensorReading':
            return 'brise'
        if name == 'PavimentosSensorReading':
            return 'pavimentos'
        return 'default'

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)

    def allow_relation(self, obj1, obj2, **hints):
        db1 = self.db_for_read(obj1.__class__)
        db2 = self.db_for_read(obj2.__class__)
        if db1 and db2:
            return db1 == db2
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Ensure sensor models are migrated to their databases
        if app_label == 'app':
            if model_name == 'brisesensorreading':
                return db == 'brise'
            if model_name == 'pavimentossensorreading':
                return db == 'pavimentos'
            # everything else in app -> default
            return db == 'default'
        # other apps follow default
        return None

