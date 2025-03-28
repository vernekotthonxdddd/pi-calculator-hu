import logging
import sys
import time
import multiprocessing
import psutil
from colorama import init, Fore
from mpmath import mp
import os

#By:
#lowkeyrenato
#PWD by:
#ChatGPT
#Gemini

# Inicializálja a colorama könyvtárat a színes konzol kimenethez
init(autoreset=True)

# Konfigurálja a naplózást a hibák rögzítéséhez egy fájlba
logging.basicConfig(filename="crash_log.txt", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

def set_process_priority():
    """Beállítja a processz prioritását magasra."""
    try:
        p = psutil.Process(os.getpid()) # Lekéri az aktuális processz objektumot
        p.nice(psutil.HIGH_PRIORITY_CLASS)  # Windows: Beállítja a prioritást magasra
        # p.nice(-10)  # Linux/Unix: Kommentezve, mivel Windows-ra van optimalizálva
    except Exception as e:
        logging.error(f"Sikertelen a processz prioritásának beállítása: {e}") # Naplózza a hibát
        print(f"{Fore.RED}Figyelmeztetés: Nem sikerült beállítani a processz prioritását.{Fore.RESET}") # Kiírja a figyelmeztetést a konzolra piros színnel

def calculate_pi_chunk(start, end, digits, result_queue, progress_queue):
    """Kiszámolja a Pi szám egy részletét (chunk) és jelenti az előrehaladást."""
    try:
        local_mp = mp.clone()  # Létrehoz egy másolatot a mpmath kontextusból, hogy elkerülje a globális állapot problémákat
        local_mp.dps = digits + 10 # Beállítja a pontosságot (számjegyek száma a tizedesvessző után) egy biztonsági ráhagyással
        pi_str = str(local_mp.pi) # Kiszámolja a Pi értékét stringként
        # A 2. indextől kezdődik a szeletelés, hogy kihagyja a "3." előtagot
        chunk = pi_str[2:digits+2] # Kivágja a kívánt számú számjegyet a Pi stringből
        result_queue.put(chunk) # Elküldi a kiszámolt részletet az eredmény sorba (queue)
        progress_queue.put(100)  # Jelzi, hogy a számítás befejeződött (100%-os előrehaladás)
    except Exception as e:
        logging.error(f"Hiba a Pi részlet kiszámításakor: {e}") # Naplózza a hibát
        result_queue.put(None)  # Jelzi a fő processznek, hogy hiba történt
        progress_queue.put(0)  # Jelzi, hogy a számítás sikertelen (0%-os előrehaladás)

def save_to_file(pi_value, digits):
    """Elmenti a Pi értékét egy fájlba."""
    try:
        filename = f"pi_{digits}.txt" # Létrehozza a fájlnevet a számjegyek számával
        with open(filename, "w") as f: # Megnyitja a fájlt írásra
            f.write("3." + pi_value) # Beírja a fájlba a Pi értékét "3." előtaggal
        print(f"{Fore.GREEN}Pi ({digits} számjegy) elmentve: {filename}{Fore.RESET}") # Kiírja a sikeres mentést zöld színnel
    except Exception as e:
        logging.error(f"Hiba a Pi fájlba mentésekor: {e}") # Naplózza a hibát
        print(f"{Fore.RED}Hiba a Pi fájlba mentésekor.{Fore.RESET}") # Kiírja a hibaüzenetet piros színnel

def main():
    start_time = time.time() # Rögzíti a program indulási idejét

    try:
        digits = int(input("Adja meg a Pi számjegyek számát, amelyet generálni szeretne: ")) # Bekéri a felhasználótól a számjegyek számát
        if digits <= 0:
            raise ValueError("A számjegyek számának pozitívnak kell lennie.") # Hibát dob, ha a számjegyek száma nem pozitív

        print("A Pi számítás elkezdődött...")

        cpu_count = multiprocessing.cpu_count() # Lekéri a processzor magok számát
        num_processes = cpu_count * 4 # Aggresszívan növeli a processzek számát (magok száma * 4)

        # Nincs szükség a chunking-ra (darabolásra), mert egyszerre számoljuk ki a teljes Pi értéket
        chunks = [(0,digits)] # Létrehoz egyetlen chunk-ot a teljes számjegy tartományra

        result_queue = multiprocessing.Queue() # Létrehoz egy sort (queue) az eredmények fogadásához
        progress_queue = multiprocessing.Queue() # Létrehoz egy sort az előrehaladás figyeléséhez
        processes = [] # Létrehoz egy listát a processzek tárolására

        # Processzek létrehozása
        for chunk_start, chunk_end in chunks:
            p = multiprocessing.Process(target=calculate_pi_chunk, args=(chunk_start, chunk_end, digits, result_queue, progress_queue)) # Létrehoz egy processzt a Pi részlet kiszámításához
            processes.append(p) # Hozzáadja a processzt a listához
            p.start() # Elindítja a processzt

        set_process_priority()  # Beállítja a fő processz prioritását

        # Előrehaladás figyelése és az eredmények összesítése
        pi_value = "" # Inicializálja a Pi értékét
        num_errors = 0 # Inicializálja a hibák számát
        completed_chunks = 0 # Inicializálja a befejezett chunk-ok számát
        total_chunks = len(processes) # Lekéri az összes chunk számát (ami most 1)

        while completed_chunks < total_chunks: # Amíg nem fejeződött be az összes chunk
            try:
                progress = progress_queue.get(timeout=0.1) # Nem blokkoló sorból való olvasás 0.1 másodperces időkorláttal
                if progress == 100: # Ha az előrehaladás 100%
                    completed_chunks += 1 # Növeli a befejezett chunk-ok számát
                    chunk_result = result_queue.get() # Lekéri a chunk eredményét
                    if chunk_result is None: # Ha az eredmény None (hiba történt)
                        num_errors += 1 # Növeli a hibák számát
                        print(f"{Fore.RED}Hiba: Egy processz nem tudta kiszámítani a részletet.{Fore.RESET}") # Kiírja a hibaüzenetet piros színnel
                    else:
                        pi_value += chunk_result # Hozzáadja a részletet a Pi értékhez
                else:
                    num_errors +=1
                    completed_chunks+=1
                    print(f"{Fore.RED}Hiba: Egy processz nem tudta kiszámítani a részletet.{Fore.RESET}")


            except multiprocessing.queues.Empty:
                pass # Nincs előrehaladás, folytatja a ciklust

            # Kiszámolja a teljes előrehaladást (ami most mindig 100%)
            overall_progress = (completed_chunks / total_chunks) * 100
            print(f"\rElőrehaladás: {overall_progress:.2f}%", end="") # Kiírja az előrehaladást a konzolra
            sys.stdout.flush() # Kiüríti a kimeneti puffert, hogy azonnal megjelenjen az előrehaladás

        print() # Új sor a konzolon, miután az előrehaladás befejeződött

        if num_errors > 0: # Ha több mint 0 hiba történt
            print(f"{Fore.RED}Hiba: A számítás sikertelen, {num_errors} hibával.{Fore.RESET}") # Kiírja a hibaüzenetet piros színnel
            return # Kilép a programból

        # Memóriahasználat
        memory_usage_mb = psutil.virtual_memory().used / (1024 ** 2) # Kiszámolja a memóriahasználatot MB-ban
        print(f"{Fore.BLUE}Memóriahasználat: {memory_usage_mb:.2f} MB{Fore.RESET}") # Kiírja a memóriahasználatot kék színnel

        # Mentés fájlba (a fő processzben az egyszerűség és a hibakezelés érdekében)
        save_to_file(pi_value, digits) # Elmenti a Pi értéket egy fájlba

        # Számítási idő
        end_time = time.time() # Rögzíti a program befejezési idejét
        elapsed_time = end_time - start_time # Kiszámolja az eltelt időt
        print(f"{Fore.YELLOW}Számítási idő: {elapsed_time:.2f} másodperc{Fore.RESET}") # Kiírja a számítási időt sárga színnel

    except ValueError as ve: # Kezeli a ValueError kivételt (pl. nem számot ad meg a felhasználó)
        print(f"{Fore.RED}Érvénytelen bemenet: {ve}{Fore.RESET}") # Kiírja a hibaüzenetet piros színnel
    except Exception as e: # Kezeli az összes többi kivételt
        logging.error(f"Váratlan hiba történt: {e}") # Naplózza a hibát
        print(f"{Fore.RED}Váratlan hiba történt: {e}{Fore.RESET}") # Kiírja a hibaüzenetet piros színnel

    finally:
        input("Nyomjon Entert a kilépéshez...") # Vár a felhasználóra, hogy nyomjon Entert a kilépéshez

if __name__ == "__main__":
    main() # Meghívja a main() függvényt, ha a szkript közvetlenül fut