"""spending.py"""

class Spending:
    """
    A Spending osztály a statisztikában tárolt kiadási adatokat reprezentálja.
    """

    def __init__(self, avg: float, monthly_avg: float, monthly_sum: float, total: float):
        """
        Inicializálja a kiadás attribútumait.

        Args:
            avg (float): Átlagos kiadás.
            monthly_avg (float): Havi átlagos kiadás.
            monthly_sum (float): Havi kiadások összege.
            total (float): Összesített kiadás.
        """
        self._avg = avg
        self._monthly_avg = monthly_avg
        self._monthly_sum = monthly_sum
        self._total = total

    @property
    def avg(self):
        """Visszaadja az átlagos kiadást."""
        return self._avg

    @avg.setter
    def avg(self, value: float):
        """Beállítja az átlagos kiadást."""
        if value < 0:
            raise ValueError("Az átlagos kiadás nem lehet negatív.")
        self._avg = value

    @property
    def monthly_avg(self):
        """Visszaadja a havi átlagos kiadást."""
        return self._monthly_avg

    @monthly_avg.setter
    def monthly_avg(self, value: float):
        """Beállítja a havi átlagos kiadást."""
        if value < 0:
            raise ValueError("A havi átlagos kiadás nem lehet negatív.")
        self._monthly_avg = value

    @property
    def monthly_sum(self):
        """Visszaadja a havi kiadások összegét."""
        return self._monthly_sum

    @monthly_sum.setter
    def monthly_sum(self, value: float):
        """Beállítja a havi kiadások összegét."""
        if value < 0:
            raise ValueError("A havi kiadások összege nem lehet negatív.")
        self._monthly_sum = value

    @property
    def total(self):
        """Visszaadja az összesített kiadást."""
        return self._total

    @total.setter
    def total(self, value: float):
        """Beállítja az összesített kiadást."""
        if value < 0:
            raise ValueError("Az összesített kiadás nem lehet negatív.")
        self._total = value

    def to_dict(self):
            """
            Átalakítja a Spending objektumot szótárrá.

            Return:
                dict: A kiadási adatokat tartalmazó szótár.
            """
            return {
                'avg': self.avg,
                'monthly_avg': self.monthly_avg,
                'monthly_sum': self.monthly_sum,
                'total': self.total
            }