import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk

from parser_utils import extract_valid_wallets, export_rows_to_csv
from api_client import fetch_wallet_chain_balance, SUPPORTED_CHAINS

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class WalletCheckerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Multi-Chain Wallet Balance Checker")
        self.geometry("820x580")
        self.minsize(680, 500)

        self.selected_file_path = None
        self.results_data = []
        self.is_scanning = False

        self.setup_ui()

    def setup_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # --- BLOCK 1: API Key Input ---
        lbl_api = ctk.CTkLabel(main_frame, text="Enter API Key:", anchor="w")
        lbl_api.pack(fill="x", pady=(0, 2))

        self.entry_api_key = ctk.CTkEntry(
            main_frame, placeholder_text="Paste your Web3 API Key...", show="*"
        )
        self.entry_api_key.pack(fill="x", pady=(0, 10))

        # --- BLOCK 2: Manual Wallet Addresses Input ---
        lbl_wallets_input = ctk.CTkLabel(
            main_frame,
            text="Paste wallet addresses (comma or newline separated):",
            anchor="w",
        )
        lbl_wallets_input.pack(fill="x", pady=(0, 2))

        self.entry_manual_wallets = ctk.CTkEntry(
            main_frame, placeholder_text="0x123..., 0x456... (optional if file is selected)"
        )
        self.entry_manual_wallets.pack(fill="x", pady=(0, 10))

        # --- BLOCK 3: File Selection Button ---
        lbl_file = ctk.CTkLabel(
            main_frame, text="Select file with wallets (.txt):", anchor="w"
        )
        lbl_file.pack(fill="x", pady=(0, 2))

        self.btn_select_file = ctk.CTkButton(
            main_frame,
            text="Select File",
            fg_color="#E0E0E0",
            text_color="#111111",
            hover_color="#D0D0D0",
            command=self.select_file,
        )
        self.btn_select_file.pack(fill="x", pady=(0, 10))

        # --- BLOCK 4: Start Balance Check Button ---
        self.btn_check = ctk.CTkButton(
            main_frame,
            text="Check Balances",
            command=self.start_checking,
        )
        self.btn_check.pack(fill="x", pady=(0, 12))

        # --- BLOCK 5: Results Table ---
        table_frame = tk.Frame(main_frame, bd=1, relief="solid")
        table_frame.pack(fill="both", expand=True, pady=(0, 10))

        columns = ("address", "network", "native_balance", "tokens_usd", "total_usd")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )

        self.tree.heading("address", text="Wallet Address")
        self.tree.heading("network", text="Network")
        self.tree.heading("native_balance", text="Native Balance")
        self.tree.heading("tokens_usd", text="Tokens (USD)")
        self.tree.heading("total_usd", text="Total (USD)")

        self.tree.column("address", width=260, anchor="w")
        self.tree.column("network", width=110, anchor="center")
        self.tree.column("native_balance", width=140, anchor="e")
        self.tree.column("tokens_usd", width=120, anchor="e")
        self.tree.column("total_usd", width=120, anchor="e")

        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- BLOCK 6: Status Bar and Save to CSV Button ---
        self.lbl_status = ctk.CTkLabel(
            main_frame, text="Ready. Total Portfolio: $0.00", anchor="w", text_color="gray"
        )
        self.lbl_status.pack(fill="x", pady=(0, 5))

        self.btn_export = ctk.CTkButton(
            main_frame,
            text="Save to CSV",
            fg_color="#E0E0E0",
            text_color="#111111",
            hover_color="#D0D0D0",
            command=self.export_csv,
        )
        self.btn_export.pack(fill="x")

    # --- EVENT HANDLERS ---
    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Wallets File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if file_path:
            self.selected_file_path = file_path
            filename = file_path.split("/")[-1]
            self.btn_select_file.configure(text=f"Selected: {filename}")
            self.lbl_status.configure(text=f"Loaded file: {filename}")

    def start_checking(self):
        if self.is_scanning:
            return

        api_key = self.entry_api_key.get().strip()
        if not api_key:
            messagebox.showwarning("Missing API Key", "Please enter your Moralis API Key first.")
            return

        manual_text = self.entry_manual_wallets.get()
        wallets = extract_valid_wallets(manual_text, self.selected_file_path)

        if not wallets:
            messagebox.showwarning(
                "No Wallets Found",
                "Please enter at least one valid EVM address (0x...) or select a .txt file.",
            )
            return

        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results_data.clear()

        # Lock button and start background worker thread
        self.is_scanning = True
        self.btn_check.configure(state="disabled", text="Scanning...")
        thread = threading.Thread(
            target=self.run_scan_worker, args=(api_key, wallets), daemon=True
        )
        thread.start()

    def run_scan_worker(self, api_key: str, wallets: list[str]):
        """Background thread worker to fetch balances without freezing the GUI."""
        grand_total_usd = 0.0
        total_tasks = len(wallets) * len(SUPPORTED_CHAINS)
        completed_tasks = 0

        try:
            for wallet in wallets:
                for chain_id in SUPPORTED_CHAINS:
                    completed_tasks += 1
                    self.after(
                        0,
                        lambda c=completed_tasks, t=total_tasks, w=wallet: self.lbl_status.configure(
                            text=f"Scanning [{c}/{t}]: {w[:10]}... ({SUPPORTED_CHAINS[chain_id]})"
                        ),
                    )

                    result = fetch_wallet_chain_balance(api_key, wallet, chain_id)

                    # Only display rows where there is a non-zero balance or native tokens
                    if result["total_usd"] > 0 or not result["native_balance"].startswith("0.0000"):
                        grand_total_usd += result["total_usd"]
                        row_tuple = (
                            result["address"],
                            result["network"],
                            result["native_balance"],
                            f"${result['tokens_usd']:,.2f}",
                            f"${result['total_usd']:,.2f}",
                        )
                        self.results_data.append(row_tuple)
                        self.after(0, lambda r=row_tuple: self.tree.insert("", "end", values=r))

                    # Small delay to respect free API rate limits
                    time.sleep(0.15)

            self.after(
                0,
                lambda tot=grand_total_usd: self.lbl_status.configure(
                    text=f"Scan complete. Wallets checked: {len(wallets)} | Total Portfolio: ${tot:,.2f}"
                ),
            )
        except Exception as e:
            self.after(0, lambda err=str(e): messagebox.showerror("API Error", f"Failed to fetch data:\n{err}"))
            self.after(0, lambda: self.lbl_status.configure(text="Scan interrupted due to error."))
        finally:
            self.is_scanning = False
            self.after(0, lambda: self.btn_check.configure(state="normal", text="Check Balances"))

    def export_csv(self):
        if not self.results_data:
            messagebox.showinfo("No Data", "Nothing to export yet. Run a balance check first.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save Report as CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile="wallet_balances_report.csv",
        )
        if save_path:
            export_rows_to_csv(save_path, self.results_data)
            messagebox.showinfo("Success", f"Report saved to:\n{save_path}")


if __name__ == "__main__":
    app = WalletCheckerApp()
    app.mainloop()