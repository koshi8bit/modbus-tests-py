import asyncio
import random

from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusSequentialDataBlock,
    ModbusServerContext,
)
from pymodbus.server import ModbusTcpServer


# ============================================================
# Настройки Modbus TCP
# ============================================================

HOST = "0.0.0.0"
PORT = 5020
DEVICE_ID = 1

# Количество элементов в каждой области
SIZE = 1000


# ============================================================
# Function Codes
# ============================================================

FC_COIL = 1
FC_DISCRETE_INPUT = 2
FC_HOLDING_REGISTER = 3
FC_INPUT_REGISTER = 4


# ============================================================
# Modbus datastore
#
# В pymodbus 3.15.x здесь нужно использовать адрес 1,
# потому что ModbusDeviceContext внутри выполняет смещение.
#
# При этом со стороны Modbus-клиента адреса остаются 0..999.
# ============================================================

device = ModbusDeviceContext(
    di=ModbusSequentialDataBlock(1, [False] * SIZE),
    co=ModbusSequentialDataBlock(1, [False] * SIZE),
    ir=ModbusSequentialDataBlock(1, [0] * SIZE),
    hr=ModbusSequentialDataBlock(1, [0] * SIZE),
)

context = ModbusServerContext(
    devices={DEVICE_ID: device},
    single=False,
)


# ============================================================
# CLI help
# ============================================================

HELP = """
Команды:

  set di <addr> <0|1>
  set co <addr> <0|1>
  set ir <addr> <value>
  set hr <addr> <value>

  get di <addr> [count]
  get co <addr> [count]
  get ir <addr> [count]
  get hr <addr> [count]

  dump di <start> <count>
  dump co <start> <count>
  dump ir <start> <count>
  dump hr <start> <count>

  help
  quit


Примеры:

  set di 0 1
  set co 10 1
  set ir 20 1234
  set hr 100 65535

  get di 0
  get hr 100
  get hr 100 10

  dump co 0 20
  dump ir 0 10
"""


# ============================================================
# Вспомогательные функции
# ============================================================

def get_fc(area: str) -> int:
    areas = {
        "co": FC_COIL,
        "coil": FC_COIL,
        "coils": FC_COIL,

        "di": FC_DISCRETE_INPUT,
        "discrete": FC_DISCRETE_INPUT,

        "hr": FC_HOLDING_REGISTER,
        "holding": FC_HOLDING_REGISTER,

        "ir": FC_INPUT_REGISTER,
        "input": FC_INPUT_REGISTER,
    }

    try:
        return areas[area.lower()]
    except KeyError:
        raise ValueError(
            "Неизвестная область. Используйте di, co, ir или hr."
        )


def normalize_value(fc: int, value: int):
    """
    Проверка значения перед записью.
    """

    if fc in (FC_COIL, FC_DISCRETE_INPUT):
        if value not in (0, 1):
            raise ValueError(
                "Для Discrete Input / Coil значение должно быть 0 или 1."
            )

        return bool(value)

    if not 0 <= value <= 65535:
        raise ValueError(
            "Значение регистра должно быть в диапазоне 0..65535."
        )

    return value


def check_address(address: int, count: int = 1):
    """
    Проверка Modbus-адреса.
    """

    if address < 0:
        raise ValueError(
            "Адрес не может быть отрицательным."
        )

    if count <= 0:
        raise ValueError(
            "Количество должно быть больше нуля."
        )

    if address + count > SIZE:
        raise ValueError(
            f"Выход за диапазон памяти. "
            f"Доступны адреса 0..{SIZE - 1}."
        )


# ============================================================
# АВТОМАТИЧЕСКОЕ ИЗМЕНЕНИЕ INPUT REGISTERS
# ============================================================

async def update_input_registers(server: ModbusTcpServer):
    """
    Эта функция вызывается один раз в секунду.

    Здесь можно реализовать любое поведение
    эмулируемого устройства.

    Текущее назначение регистров:

      IR[0] - температура * 10
              20.0 .. 30.0 °C

      IR[1] - давление * 100
              9.50 .. 10.50 bar

      IR[2] - RPM
              1400 .. 1600

      IR[3] - счётчик секунд

      IR[4] - случайное значение 0..65535

      IR[5] - пилообразный сигнал 0..1000
    """

    # --------------------------------------------------------
    # Получаем текущие значения
    # --------------------------------------------------------
    return

    current = await server.async_getValues(
        DEVICE_ID,
        FC_INPUT_REGISTER,
        0,
        6,
    )

    # --------------------------------------------------------
    # IR[0] - температура
    # --------------------------------------------------------

    temperature = random.randint(200, 300)

    # 200 -> 20.0 °C
    # 253 -> 25.3 °C
    # 300 -> 30.0 °C


    # --------------------------------------------------------
    # IR[1] - давление
    # --------------------------------------------------------

    pressure = random.randint(950, 1050)

    # 950  -> 9.50 bar
    # 1000 -> 10.00 bar
    # 1050 -> 10.50 bar


    # --------------------------------------------------------
    # IR[2] - обороты двигателя
    # --------------------------------------------------------

    rpm = random.randint(1400, 1600)


    # --------------------------------------------------------
    # IR[3] - счётчик секунд
    # --------------------------------------------------------

    counter = (current[3] + 1) & 0xFFFF


    # --------------------------------------------------------
    # IR[4] - случайное 16-битное значение
    # --------------------------------------------------------

    random_value = random.randint(0, 9)


    # --------------------------------------------------------
    # IR[5] - пилообразный сигнал
    # --------------------------------------------------------

    saw = current[5] + 10

    if saw > 1000:
        saw = 0


    # --------------------------------------------------------
    # Формируем значения
    # --------------------------------------------------------

    values = [
        temperature,     # IR[0]
        pressure,        # IR[1]
        rpm,             # IR[2]
        counter,         # IR[3]
        random_value,    # IR[4]
        saw,             # IR[5]
    ]


    # --------------------------------------------------------
    # Записываем сразу несколько Input Registers
    # --------------------------------------------------------

    await server.async_setValues(
        DEVICE_ID,
        FC_INPUT_REGISTER,
        0,
        values,
    )


    # --------------------------------------------------------
    # Вывод для отладки
    # --------------------------------------------------------

    print(
        "[AUTO] "
        f"IR[0]={temperature} ({temperature / 10:.1f} °C), "
        f"IR[1]={pressure} ({pressure / 100:.2f} bar), "
        f"IR[2]={rpm} RPM, "
        f"IR[3]={counter}, "
        f"IR[4]={random_value}, "
        f"IR[5]={saw}"
    )


# ============================================================
# Периодическая задача
# ============================================================

async def input_registers_task(server: ModbusTcpServer):
    """
    Бесконечный цикл.

    Раз в секунду вызывает update_input_registers().
    """

    while True:
        try:
            await update_input_registers(server)

        except asyncio.CancelledError:
            # Задача была остановлена при завершении программы
            raise

        except Exception as exc:
            print(
                f"[AUTO] Ошибка обновления Input Registers: "
                f"{type(exc).__name__}: {exc}"
            )

        await asyncio.sleep(1)


# ============================================================
# CLI
# ============================================================

async def cli(server: ModbusTcpServer):

    print(HELP)

    while True:

        try:
            # input() является блокирующей функцией,
            # поэтому выполняем её в отдельном потоке.
            line = await asyncio.to_thread(
                input,
                "modbus> "
            )

        except (EOFError, KeyboardInterrupt):
            break

        line = line.strip()

        if not line:
            continue

        parts = line.split()

        command = parts[0].lower()

        try:

            # =================================================
            # EXIT
            # =================================================

            if command in (
                "quit",
                "exit",
                "q",
            ):
                break


            # =================================================
            # HELP
            # =================================================

            if command in (
                "help",
                "?",
            ):
                print(HELP)
                continue


            # =================================================
            # SET
            # =================================================

            if command == "set":

                if len(parts) != 4:
                    print(
                        "Формат: "
                        "set <di|co|ir|hr> <address> <value>"
                    )
                    continue

                area = parts[1]

                address = int(
                    parts[2],
                    0
                )

                value_raw = int(
                    parts[3],
                    0
                )

                fc = get_fc(area)

                check_address(
                    address
                )

                value = normalize_value(
                    fc,
                    value_raw
                )

                await server.async_setValues(
                    DEVICE_ID,
                    fc,
                    address,
                    [value],
                )

                if isinstance(value, bool):
                    print(
                        f"{area.upper()}[{address}] "
                        f"= {int(value)}"
                    )

                else:
                    print(
                        f"{area.upper()}[{address}] "
                        f"= {value}"
                    )

                continue


            # =================================================
            # GET / DUMP
            # =================================================

            if command in (
                "get",
                "dump",
            ):

                if command == "get":

                    if len(parts) not in (
                        3,
                        4,
                    ):

                        print(
                            "Формат: "
                            "get <di|co|ir|hr> "
                            "<address> [count]"
                        )

                        continue

                    area = parts[1]

                    address = int(
                        parts[2],
                        0
                    )

                    if len(parts) == 4:
                        count = int(
                            parts[3],
                            0
                        )
                    else:
                        count = 1


                else:

                    if len(parts) != 4:

                        print(
                            "Формат: "
                            "dump <di|co|ir|hr> "
                            "<start> <count>"
                        )

                        continue

                    area = parts[1]

                    address = int(
                        parts[2],
                        0
                    )

                    count = int(
                        parts[3],
                        0
                    )


                fc = get_fc(area)

                check_address(
                    address,
                    count
                )


                values = await server.async_getValues(
                    DEVICE_ID,
                    fc,
                    address,
                    count,
                )


                print()

                for offset, value in enumerate(values):

                    addr = address + offset

                    if fc in (
                        FC_COIL,
                        FC_DISCRETE_INPUT,
                    ):
                        value = int(
                            bool(value)
                        )

                    print(
                        f"{area.upper()}[{addr:5}] = {value}"
                    )

                print()

                continue


            # =================================================
            # UNKNOWN
            # =================================================

            print(
                "Неизвестная команда. "
                "Введите help."
            )


        except ValueError as exc:

            print(
                f"Ошибка: {exc}"
            )


        except Exception as exc:

            print(
                f"Ошибка: "
                f"{type(exc).__name__}: {exc}"
            )


    print(
        "\nОстановка сервера..."
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    # --------------------------------------------------------
    # Создание TCP сервера
    # --------------------------------------------------------

    server = ModbusTcpServer(
        context=context,
        address=(
            HOST,
            PORT,
        ),
    )


    # --------------------------------------------------------
    # Запуск Modbus сервера
    # --------------------------------------------------------

    await server.serve_forever(
        background=True
    )


    print()
    print("=" * 70)
    print("Modbus TCP simulator запущен")
    print()
    print(
        f"Адрес:       {HOST}:{PORT}"
    )
    print(
        f"Device ID:   {DEVICE_ID}"
    )
    print(
        f"Адреса:      0..{SIZE - 1}"
    )
    print()
    print(
        "Input Registers автоматически "
        "обновляются раз в секунду."
    )
    print("=" * 70)
    print()


    # --------------------------------------------------------
    # Запускаем периодическое обновление Input Registers
    # --------------------------------------------------------

    update_task = asyncio.create_task(
        input_registers_task(
            server
        )
    )


    try:

        # ----------------------------------------------------
        # Запускаем консоль
        # ----------------------------------------------------

        await cli(
            server
        )


    finally:

        # ----------------------------------------------------
        # Останавливаем периодическую задачу
        # ----------------------------------------------------

        update_task.cancel()

        try:
            await update_task

        except asyncio.CancelledError:
            pass


        # ----------------------------------------------------
        # Останавливаем Modbus TCP server
        # ----------------------------------------------------

        await server.shutdown()

        print(
            "Modbus TCP simulator остановлен."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        asyncio.run(
            main()
        )

    except KeyboardInterrupt:
        print(
            "\nПрограмма остановлена."
        )