import datetime
import json
from .clients.SQL_client import PSQLClient
from matplotlib import use
import matplotlib.pyplot as plt
from numpy import array
from PIL import Image
from io import BytesIO


class DBAccessManager:
    __slots__ = ("db_client", "RELAPSE_POLL_OPTIONS", "DEPRESSION_POLL_OPTIONS", "DRINKS_PERCENTAGE")

    def __init__(self,
                 fp_relapse_criteria: str,
                 fp_depression_criteria: str,
                 fp_drinks_percentage: str,
                 db_client: PSQLClient):
        self.db_client = db_client
        try:
            with open(fp_relapse_criteria) as fr:
                lines = fr.readlines()
                self.RELAPSE_POLL_OPTIONS = [list(option_string.rsplit(maxsplit=1)) for option_string in lines]
            with open(fp_depression_criteria) as fr:
                lines = fr.readlines()
                self.DEPRESSION_POLL_OPTIONS = [list(option_string.rsplit(maxsplit=1)) for option_string in lines]
            self.DRINKS_PERCENTAGE = json.loads(open(fp_drinks_percentage).read())
        except Exception as err:
            raise Exception("Resource files are unavailable: ", err)

    def get_user(self, id: int):
        users_info = self.db_client.execute_DQL_command(f"""
            SELECT * 
            FROM users
            WHERE id = %s;
        """, (id,))
        return users_info[0] if users_info else None

    def create_user(self, id: int, username: str):
        self.db_client.execute_DML_command("""
            INSERT INTO users (id, username)
            VALUES (%s, %s);
        """, (id, username))

    def update_test(self, id: int, date: datetime, dp_results=None, rl_results=None):
        rl_results = "" if rl_results is None else self.__answers_processing(rl_results, "relapse")
        dp_results = "" if dp_results is None else self.__answers_processing(dp_results, "depression")

        if dp_results:
            self.db_client.execute_DML_command("""
                INSERT INTO depression_poll
                VALUES (%s, %s, %s);
            """, (id, dp_results, date)
                                               )
        if rl_results:
            self.db_client.execute_DML_command("""
                INSERT INTO relapse_poll
                VALUES (%s, %s, %s);
            """, (id, rl_results, date)
                                               )

    def __answers_processing(self, answers, poll_type: str):
        groups_counter = [0, 0, 0]
        if poll_type == "depression":
            for ans in answers:
                groups_counter[int(self.DEPRESSION_POLL_OPTIONS[ans][1])] += 1
        elif poll_type == "relapse":
            for ans in answers:
                groups_counter[int(self.RELAPSE_POLL_OPTIONS[ans][1])] += 1
        return "".join([str(cntr) for cntr in groups_counter])

    def create_poll_statistics(self, user_id: int):
        dp_answers = self.db_client.execute_DQL_command("""
                    SELECT answers, date
                    FROM depression_poll
                    WHERE user_id = %s
                    ORDER BY date;
                """, (user_id,))
        rl_answers = self.db_client.execute_DQL_command(f"""
                    SELECT answers, date
                    FROM relapse_poll
                    WHERE user_id = %s
                    ORDER BY date;
                """, (user_id,))
        if not (dp_answers and rl_answers):
            return None

        dp_points = []
        rl_points = []
        dp_dates = []
        rl_dates = []
        for test_result in dp_answers:
            dp_points.append([3 - int(c) for c in test_result[0]])
            dp_dates.append(test_result[1].strftime("%d/%m"))
        for test_result in rl_answers:
            rl_points.append([3 - int(c) for c in test_result[0]])
            rl_dates.append(test_result[1].strftime("%d/%m"))

        use("Agg")
        figure, (axis1, axis2) = plt.subplots(2, 1)

        colors = ("indigo", "blue", "plum")
        labels = ("emotional state", "relationships and\nprofessional activity", "physical state")

        for points, axis, dates in ((dp_points, axis1, dp_dates), (rl_points, axis2, rl_dates)):
            if points:
                for i in range(3):
                    axis.plot(array(list(range(1, len(points) + 1))),
                              array([int(point[i]) for point in points]),
                              color=colors[i],
                              label=labels[i],
                              marker='o',
                              markersize='4',
                              linewidth='2')
                axis.plot(array(list(range(1, len(points) + 1))),
                          array([sum(point) for point in points]),
                          color='black',
                          linestyle="-",
                          linewidth="3",
                          label="General trend")
                axis.set_ylim([-1, 15])
                axis.set_xticks(ticks=list(range(1, len(points) + 1)), labels=dates, rotation=20)
                axis.legend(fontsize=7)
                axis.grid()

        axis1.set_title(label="General emotional state tracker")
        axis2.set_title(label="Relapse factors tracker")
        figure.tight_layout()

        bytes_io = BytesIO()
        plt.savefig(bytes_io)
        bytes_io.seek(0)
        image = Image.open(bytes_io)

        return image

    def update_month_calendar(self, user_id: int, day: datetime.date, dose_string: str):
        ethanol_equivalent = self.__calculate_dose(dose_string)
        self.db_client.execute_DML_command(
            """
            INSERT INTO month_statistics (user_id, day, ethanol_equivalent)
            VALUES (%s, %s, %s);
            """, (user_id, day, ethanol_equivalent))
        self.db_client.execute_DML_command(
            """
            DELETE FROM month_statistics
            WHERE user_id = %s AND day < %s - '1 month'::interval;
            """, (user_id, day)
        )

    def __calculate_dose(self, dose_string: str):
        day_drinks_and_doses = {}
        for str_drink in dose_string.split(sep=','):
            ml, type_of_drink = str_drink.split(maxsplit=1)
            day_drinks_and_doses[type_of_drink.lower()] = int(ml)

        sum_of_ethanol = 0.0
        for type_of_drink, ml in day_drinks_and_doses.items():
            sum_of_ethanol += float(int(ml) / 100 * self.DRINKS_PERCENTAGE[type_of_drink])

        return sum_of_ethanol

    def create_dose_statistics(self, user_id: int):
        user_doses = self.db_client.execute_DQL_command("""
            SELECT day, ethanol_equivalent
            FROM month_statistics
            WHERE user_id = %s
            ORDER BY day;
        """, (user_id,))
        if not user_doses:
            return None

        use("Agg")

        doses_per_day = array([day_stat[1] for day_stat in user_doses])
        dates = array(["{}, {}".format(str(day_stat[0].day), day_stat[0].strftime("%a")) for
                       day_stat in user_doses])

        plt.bar(x=dates,
                height=doses_per_day,
                label="Ethanol equivalent per day.",
                color=[self.__choose_color(ml) for ml in doses_per_day]
                )
        plt.title("Ethanol consumption in " + user_doses[0][0].strftime("%B"))
        plt.ylabel("ml")
        plt.xticks(rotation=30)

        bytes_io = BytesIO()
        plt.savefig(bytes_io)
        bytes_io.seek(0)
        image = Image.open(bytes_io)

        return image

    @staticmethod
    def __choose_color(ml_per_day: int):
        if ml_per_day < 20:
            return "yellowgreen"
        elif ml_per_day < 50:
            return "goldenrod"
        else:
            return "crimson"
