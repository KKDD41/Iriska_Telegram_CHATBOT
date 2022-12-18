import sqlite3


class SQLiteClient:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.conn = None

    def create_conn(self):
        self.conn = sqlite3.connect(self.filepath, check_same_thread=False)

    def execute_query(self, command: str, params: tuple = ()):
        if self.conn is not None:
            try:
                self.conn.execute(command, params)
                self.conn.commit()
            except Exception as error:
                raise error.__class__("Command or params in 'SQLClient.execute_query' are invalid.")
        else:
            raise ConnectionError("There is no definition for field 'self.conn'.")

    def execute_select_query(self, command: str):
        if self.conn is not None:
            try:
                curr = self.conn.cursor()
                curr.execute(command)
                return curr.fetchall()
            except Exception as error:
                raise error.__class__("Command in 'SQLClient.execute_select_query' is invalid.")
        else:
            raise ConnectionError("There is no definition for field 'self.conn'.")


if __name__ == "__main__":
    scl = SQLiteClient("C:\\Users\\Kate\\Desktop\\IRISKA\\Irirska-TelegramChatBot\\databases\\users.db")
    scl.create_conn()
    scl.conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id text PRIMARY KEY,
            chat_id integer,
            username text,
            dp_results text,
            rl_results text,
            number_of_day integer,
            data text
        );
    """)
    scl = SQLiteClient("C:\\Users\\Kate\\Desktop\\IRISKA\\Irirska-TelegramChatBot\\databases\\alarm.db")
    scl.create_conn()
    scl.conn.execute("""
        CREATE TABLE IF NOT EXISTS alarm (
            time text, 
            chats_to_notify text, 
            notification_messages text
        );
    """)

