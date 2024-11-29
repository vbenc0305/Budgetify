"""income.py"""

class Income:
    """
    Az Income osztály a statisztikában tárolt bevételi adatokat reprezentálja.
    """

    def __init__(self, avg: float, monthly_avg: float, monthly_sum: float, total: float):
        """
        Inicializálja a bevétel attribútumait.

        Args:
            avg (float): Átlagos bevétel.
            monthly_avg (float): Havi átlagos bevétel.
            monthly_sum (float): Havi bevétel összege.
            total (float): Összesített bevétel.
        """
        self._avg = avg
        self._monthly_avg = monthly_avg
        self._monthly_sum = monthly_sum
        self._total = total

    @property
    def avg(self):
        """Visszaadja az átlagos bevételt."""
        return self._avg

    @avg.setter
    def avg(self, value: float):
        """Beállítja az átlagos bevételt."""
        if value < 0:
            raise ValueError("Az átlagos bevétel nem lehet negatív.")
        self._avg = value

    @property
    def monthly_avg(self):
        """Visszaadja a havi átlagos bevételt."""
        return self._monthly_avg

    @monthly_avg.setter
    def monthly_avg(self, value: float):
        """Beállítja a havi átlagos bevételt."""
        if value < 0:
            raise ValueError("A havi átlagos bevétel nem lehet negatív.")
        self._monthly_avg = value

    @property
    def monthly_sum(self):
        """Visszaadja a havi bevétel összegét."""
        return self._monthly_sum

    @monthly_sum.setter
    def monthly_sum(self, value: float):
        """Beállítja a havi bevétel összegét."""
        if value < 0:
            raise ValueError("A havi bevétel összege nem lehet negatív.")
        self._monthly_sum = value

    @property
    def total(self):
        """Visszaadja az összesített bevételt."""
        return self._total

    @total.setter
    def total(self, value: float):
        """Beállítja az összesített bevételt."""
        if value < 0:
            raise ValueError("Az összesített bevétel nem lehet negatív.")
        self._total = value

    def to_dict(self):
            """
            Átalakítja az Income objektumot szótárrá.

            Return:
                dict: A bevételi adatokat tartalmazó szótár.
            """
            return {
                'avg': self.avg,
                'monthly_avg': self.monthly_avg,
                'monthly_sum': self.monthly_sum,
                'total': self.total
            }