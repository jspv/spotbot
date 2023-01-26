from .Widgets.menu import Menu


def add_menus(menuwidget: Menu) -> None:
    menuwidget.add_menu(
        "main",
        [
            ("C", "Toggle Config Mode", "app.toggle_config_mode"),
            ("I", "Change increment µs", "load_menu('us_increment')"),
            ("N", "Change increment ∠", "load_menu('angle_increment')"),
            ("M", "Swich Mode µs/∠", "app.toggle_servo_mode"),
            None,
            ("L", "Load Config", "tbd"),
            ("S", "Save Config", "app.save_servo_config"),
            None,
            ("D", "Set Speed", "tbd"),
            ("A", "Set Acceleration", "tbd"),
            ("E", "Sequence Menu", "tbd"),
            ("Q", "<-- Back", "menu_backout"),
        ],
        title="[bold][u]Main Menu[/u][/bold]",
    )
    menuwidget.add_menu(
        "us_increment",
        [
            ("1", "1 µs", "set_us_increment(1)"),
            ("2", "2 µs", "set_us_increment(2)"),
            ("5", "5 µs", "set_us_increment(5)"),
            ("x", "10 µs", "set_us_increment(10)"),
            ("b", "20 µs", "set_us_increment(20)"),
            ("l", "50 µs", "set_us_increment(50)"),
            ("c", "100 µs", "set_us_increment(100)"),
            ("d", "200 µs", "set_us_increment(200)"),
            None,
            ("Q", "<-- Back", "menu_backout"),
        ],
        title="[bold][u]Servo Increment (µs)[u][/bold]",
    )
    menuwidget.add_menu(
        "angle_increment",
        [
            ("0", ".5°", "set_angle_increment(0.5)"),
            ("1", "1°", "set_angle_increment(1.0)"),
            ("2", "2°", "set_angle_increment(2.0)"),
            ("5", "5°", "set_angle_increment(5.0)"),
            ("x", "10°", "set_angle_increment(10.0)"),
            (
                "b",
                "[bold][underline][italics][magenta]20°[/bold][/underline][/italics][/magenta]",
                "set_angle_increment(20.0)",
            ),
            ("c", "45°", "set_angle_increment(45.0)"),
            ("d", "90°", "set_angle_increment(90.0)"),
            None,
            ("Q", "<-- Back", "menu_backout"),
        ],
        title="[bold][underline]Servo [magenta]Increment[/magenta] (∠)[/underline][/bold]",
    )
