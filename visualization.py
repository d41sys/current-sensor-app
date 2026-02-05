import os
import numpy as np
import pandas as pd
# import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
# from matplotlib.colors import Normalize
import warnings
warnings.filterwarnings('ignore')

# Constants
FARADAY = 96485.0          # C/mol
MOLAR_VOLUME_STP = 22.414  # L/mol at STP


def load_signals_from_folder(folder_path, n_segments=9, sep=","):
    """Load n_segments CSV files from folder (alphabetically sorted).
    Each file: 1st column=time, 2nd column=current, 3rd column=input.
    Automatically renames columns to 'time', 'current', 'input'.
    Returns: list of DataFrames [df0, df1, ..., df8].
    """
    files = sorted([
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith(".csv")
    ])
    if len(files) < n_segments:
        raise ValueError(f"Folder must contain at least {n_segments} CSV files. Found {len(files)}")
    files = files[:n_segments]

    dfs = []
    for f in files:
        df = pd.read_csv(f, sep=sep)
        
        # CORREZIONE: Rinomina automaticamente le prime 3 colonne
        if len(df.columns) >= 3:
            df.columns = ['time', 'current', 'input'] + list(df.columns[3:])  # Rinomina prime 3
        else:
            raise ValueError(f"File {f} must have at least 3 columns.")
        
        # Converte in numerici e rimuove NaN
        df['time'] = pd.to_numeric(df['time'], errors='coerce')
        df['current'] = pd.to_numeric(df['current'], errors='coerce')
        df = df.dropna(subset=['time', 'current'])
        
        dfs.append(df.sort_values("time"))
        print(f"Loaded {f}: {len(df)} samples")
    
    print(f" Loaded {len(dfs)} signal files successfully")
    return dfs


def get_time_window(df, window_duration_s, mode="last"):
    """Extract time window from DataFrame. mode='last': last window_duration_s seconds."""
    t = df["time"].values
    if len(t) == 0:
        return df
    t_end = t[-1]
    if mode == "last":
        t_start = max(t_end - window_duration_s, t[0])
    else:
        t_start = t[0]
    mask = (t >= t_start) & (t <= t_end)
    return df.loc[mask].copy()

def get_temporal_windows(df, window_duration_s, overlap):
    t = df["time"].values
    time_windows=[]
    time_mask=[]

    if len(t) == 0:
        return time_windows, time_mask

    if overlap >= window_duration_s:
        raise ValueError("overlap must be smaller than window_duration_s")

    t_start=t[0]
    t_end=min(t_start+window_duration_s, t[-1])
    while(t_end<=t[-1]):
        mask = (t >= t_start) & (t < t_end)
        time_windows.append(t[mask])
        time_mask.append(mask)

        t_start=t_end-overlap
        t_end=t_start+window_duration_s

    return time_windows, time_mask

def design_filter(filter_type, fs, cutoff, order=4):
    """Design Butterworth filter."""
    nyq = 0.5 * fs
    if filter_type in ("low", "high"):
        wn = cutoff / nyq
    elif filter_type == "bandpass":
        wn = [c / nyq for c in cutoff]
    else:
        raise ValueError("Invalid filter_type: use 'low', 'high', or 'bandpass'")
    b, a = butter(order, wn, btype=filter_type)
    return b, a

def apply_filter_to_df(df, filter_type, cutoff, order=4, col_in="current", col_out="current_filt"):
    """Apply Butterworth filter to current column."""
    t = df["time"].values
    i = df[col_in].values
    if len(t) < order * 3:
        return df.copy()
    dt = np.mean(np.diff(t))
    fs = 1.0 / dt
    b, a = design_filter(filter_type, fs, cutoff, order=order)
    i_filt = filtfilt(b, a, i)
    df_f = df.copy()
    df_f[col_out] = i_filt
    return df_f

def compute_stats(df, col="current_filt"):
    """Compute mean and std of column in time window."""
    if col not in df.columns:
        col = "current"
    mean_val = df[col].mean()
    std_val = df[col].std()
    return mean_val, std_val

def compute_h2_from_current(df, col="current_filt", mode="L"):
    """Compute hydrogen produced using Faraday's law: n_H2 = ∫ I(t)/(2F) dt"""
    if col not in df.columns:
        col = "current"
    t = df["time"].values
    i = df[col].values
    if len(t) < 2:
        return t, np.zeros_like(t)
    t_rel = t - t[0]
    dt = np.diff(t)
    i_mid = 0.5 * (i[1:] + i[:-1])
    Q = np.cumsum(i_mid * dt)
    n_e = Q / FARADAY
    n_h2 = n_e / 2.0
    if mode == "mol":
        h2 = n_h2
    elif mode == "L":
        h2 = n_h2 * MOLAR_VOLUME_STP
    else:
        raise ValueError("mode must be 'mol' or 'L'.")
    h2 = np.concatenate([[0.0], h2])
    return t_rel, h2

def compute_o2_from_current(df, col="current_filt", mode="L"):
    """Compute oxygen produced using Faraday's law: n_O2 = ∫ I(t)/(4F) dt"""
    if col not in df.columns:
        col = "current"

    t = df["time"].values
    i = df[col].values
    if len(t) < 2:
        return t, np.zeros_like(t)

    # relative time
    t_rel = t - t[0]

    # trapezoidal integration
    dt = np.diff(t)
    i_mid = 0.5 * (i[1:] + i[:-1])
    Q = np.cumsum(i_mid * dt)        # charge [C]

    n_e = Q / FARADAY                # moles of electrons
    n_o2 = n_e / 4.0                 # 4 e- per mole O2

    if mode == "mol":
        o2 = n_o2
    elif mode == "L":
        o2 = n_o2 * MOLAR_VOLUME_STP
    else:
        raise ValueError("mode must be 'mol' or 'L'.")

    o2 = np.concatenate([[0.0], o2])
    return t_rel, o2

# def analyze_and_plot(folder_path, window_duration_s=120, overlap=60, filter_type="low", 
#                      cutoff_hz=1.0, filter_order=4, show_plots=True):
#     """Complete analysis pipeline."""
#     print("Loading data...")
#     dfs_raw = load_signals_from_folder(folder_path)
    
#     print(f"Analyzing with: window={window_duration_s}s, filter={filter_type}, cutoff={cutoff_hz}Hz, order={filter_order}")
    
    
    
    
#     total_dfs_filtered=[]
#     total_stats=[]
#     total_h2_data=[]
#     total_o2_data=[]

#     # Extract time window
#     df=dfs_raw[0]

#     ## We assume that all files have the same FS and the same length, otherwise we need to calculate the timewindows for each file separately
#     time_windows, time_mask=get_temporal_windows(df, window_duration_s, overlap)

#     for j in range(len(time_windows)):
#         dfs_filtered = []
#         stats = []
#         h2_data = []
#         o2_data = []
#         dfs_window = []
#         for i, df in enumerate(dfs_raw):
#             df_win=df.loc[time_mask[j]].copy()
#             dfs_window.append(df_win)
            
#             # Apply filter
#             if filter_type == "bandpass":
#                 cutoff_band = [cutoff_hz/2, cutoff_hz*2]
#             else:
#                 cutoff_band = cutoff_hz
            
#             df_filt = apply_filter_to_df(df_win, filter_type, cutoff_band, filter_order)
#             dfs_filtered.append(df_filt)
            
#             # Statistics
#             mean_val, std_val = compute_stats(df_filt)
#             stats.append((mean_val, std_val))
            
#             # Hydrogen production
#             t_rel, h2 = compute_h2_from_current(df_filt)
#             h2_data.append((t_rel, h2))

#             # Oxygen production
#             t_rel_O, o2 = compute_o2_from_current(df_filt)
#             o2_data.append((t_rel_O, o2))
            
#             print(f"Segment {i+1}: Mean={mean_val:.3f}A ± {std_val:.3f}A, H2 total={h2[-1]:.4f}L")
    
#         if show_plots:
#             plot_all_figures(dfs_filtered, stats, h2_data, o2_data, window_duration_s, filter_type)

#             total_dfs_filtered.append(dfs_filtered)
#             total_stats.append(stats)
#             total_h2_data.append(h2_data)
#             total_o2_data.append(o2_data)

#     return total_dfs_filtered, total_stats, total_h2_data, total_o2_data

# def plot_all_figures(dfs_filtered, stats, h2_data, o2_data, window_duration_s, filter_type):
#     """Create all visualization figures."""
    
#     # 1. 3x3 SIGNALS PLOT
#     fig_signals, axes = plt.subplots(3, 3, figsize=(13, 10))
#     axes = axes.flatten()
    
#     for i in range(9):
#         df_filt = dfs_filtered[i]
#         t_rel = df_filt["time"].values - df_filt["time"].min()
        
#         axes[i].plot(t_rel, df_filt["current"], 'r-', alpha=0.6, linewidth=0.8, label='Raw')
#         axes[i].plot(t_rel, df_filt["current_filt"], 'b-', linewidth=1.5, label='Filtered')
        
#         mean_val, std_val = stats[i]
#         axes[i].axhline(mean_val, color='green', linestyle='--', alpha=0.8, 
#                        label=f'Mean: {mean_val:.3f}A')
#         axes[i].fill_between(t_rel, mean_val-std_val, mean_val+std_val, 
#                            alpha=0.2, color='orange', label=f'±{std_val:.3f}A')
        
#         axes[i].set_title(f'Segment {i+1}\nμ={mean_val:.3f}A ± {std_val:.3f}A', fontsize=9)
#         axes[i].grid(True, alpha=0.3)
#         axes[i].legend(fontsize=8)
#         axes[i].set_xlabel('Time (s)', fontsize=9)
#         axes[i].set_ylabel('Current (A)', fontsize=9)
    
#     plt.suptitle(f'Signals - Window: {window_duration_s}s, Filter: {filter_type}', fontsize=12)
#     plt.tight_layout()
#     plt.show()

#     #2. H2 HEATMAP + PRODUCTION PLOTS
#     fig_h2, axes_h2 = plt.subplots(2, 2, figsize=(16, 10))

#     # GRAFICO 1: H2 Production Heatmap (vertical)
#     h2_final = [data[1][-1] for data in h2_data]
#     #h2_matrix = np.array(h2_final).reshape(-1, 1)
#     h2_matrix = np.array(h2_final).reshape(3, 3)

#     im_h2 = axes_h2[0,0].imshow(h2_matrix, cmap='hot', aspect='auto')
#     axes_h2[0,0].set_title('H2 Production Heatmap')
#     axes_h2[0,0].set_xlabel('H2 (L)')
#     axes_h2[0, 0].set_xticks([0, 1, 2])
#     axes_h2[0, 0].set_yticks([0, 1, 2])
#     #axes_h2[0,0].set_xticks([0])
#     #axes_h2[0,0].set_xticklabels([''])
#     #axes_h2[0,0].set_yticks(range(9))
#     #axes_h2[0,0].set_yticklabels([f'Seg {i+1}' for i in range(9)])
#     plt.colorbar(im_h2, ax=axes_h2[0,0])

#     # GRAFICO 2: Mean Current Heatmap (vertical)
#     mean_currents = [stats[i][0] for i in range(9)]
#     current_matrix = np.array(mean_currents).reshape(3, 3)

#     im_current = axes_h2[0,1].imshow(current_matrix, cmap='Blues', aspect='auto')
#     axes_h2[0,1].set_title('Mean Current Heatmap')
#     axes_h2[0,1].set_xlabel('Current (A)')
#     axes_h2[0, 0].set_xticks([0, 1, 2])
#     axes_h2[0, 0].set_yticks([0, 1, 2])
#     plt.colorbar(im_current, ax=axes_h2[0,1])

#     # GRAFICO 3: H2 Bar Chart per segmento
#     axes_h2[1,0].bar(range(1, 10), h2_final, color='skyblue', alpha=0.8, edgecolor='navy')
#     axes_h2[1,0].set_title('Total H2 Production per Segment')
#     axes_h2[1,0].set_xlabel('Segment')
#     axes_h2[1,0].set_ylabel('H2 Volume (L)')
#     axes_h2[1,0].grid(True, alpha=0.3)

#     # GRAFICO 4: H2 Cumulative (Segment 1)
#     #t_sample, h2_sample = h2_data[0]
#     #axes_h2[1,1].plot(t_sample, h2_sample, 'g-', linewidth=2.5)
#     #axes_h2[1,1].set_title('H2 Cumulative Production\n(Segment 1)')
#     #axes_h2[1,1].set_xlabel('Time (s)')
#     #axes_h2[1,1].set_ylabel('H2 Volume (L)')
#     #axes_h2[1,1].grid(True, alpha=0.3)
#     axes_h2[1,1].set_title('H2 Cumulative Production\nAll Segments')
#     axes_h2[1,1].set_xlabel('Time (s)')
#     axes_h2[1,1].set_ylabel('H2 Volume (L)')

#     for idx, (t_seg, h2_seg) in enumerate(h2_data):
#         axes_h2[1,1].plot(t_seg, h2_seg, linewidth=1.5, label=f'Seg {idx+1}')

#     axes_h2[1,1].grid(True, alpha=0.3)
#     axes_h2[1,1].legend(fontsize=8, ncol=3)
#     plt.tight_layout()
#     plt.show()   
    
#     # 2. O2 HEATMAP + PRODUCTION PLOTS
#     fig_o2, axes_o2 = plt.subplots(1, 2, figsize=(16, 6))  # 1 row, 2 columns

#     ax_hm = axes_o2[0]   # left plot
#     ax_cum = axes_o2[1]  # right plot

#     # GRAFICO 1: O2 Production Heatmap (3x3)
#     o2_final = [data[1][-1] for data in o2_data]    # 9 final values
#     o2_matrix = np.array(o2_final).reshape(3, 3)

#     im_o2 = ax_hm.imshow(o2_matrix, cmap='hot', aspect='equal')
#     ax_hm.set_title('O2 Production Heatmap (3×3)')
#     ax_hm.set_xlabel('Column')
#     ax_hm.set_ylabel('Row')
#     ax_hm.set_xticks([0, 1, 2])
#     ax_hm.set_yticks([0, 1, 2])
#     plt.colorbar(im_o2, ax=ax_hm)

#     # GRAFICO 2: O2 Cumulative (all segments)
#     ax_cum.set_title('O2 Cumulative Production\nAll Segments')
#     ax_cum.set_xlabel('Time (s)')
#     ax_cum.set_ylabel('O2 Volume (L)')

#     for idx, (t_seg, o2_seg) in enumerate(o2_data):
#         ax_cum.plot(t_seg, o2_seg, linewidth=1.5, label=f'Seg {idx+1}')
#     ax_cum.grid(True, alpha=0.3)
#     ax_cum.legend(fontsize=8, ncol=3)

#     plt.tight_layout()
#     plt.show()

#     # 3. STATISTICS TABLE
#     fig_stats, ax_stats = plt.subplots(figsize=(12, 3))
#     ax_stats.axis('tight')
#     ax_stats.axis('off')
    
#     means = [s[0] for s in stats]
#     stds = [s[1] for s in stats]
#     h2s = h2_final
#     o2s = o2_final
    
#     table_data = [['Segment', 'Mean (A)', 'Std (A)', 'H2 (L)', 'O2 (L)']]
#     for i in range(9):
#         table_data.append([f'{i+1}', f'{means[i]:.3f}', f'{stds[i]:.3f}', f'{h2s[i]:.4f}', f'{o2s[i]:.4f}'])
    
#     table = ax_stats.table(cellText=table_data[1:], colLabels=table_data[0],
#                           cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
#     table.auto_set_font_size(False)
#     table.set_fontsize(11)
#     table.scale(1, 2.5)
    
#     ax_stats.set_title(f'SUMMARY STATISTICS - Window: {window_duration_s}s, Filter: {filter_type}', 
#                       fontsize=14, pad=20)
    
#     plt.tight_layout()
#     plt.show()
#     # stats = [(mean_1, std_1), ..., (mean_9, std_9)]
#     mean_currents = np.array([s[0] for s in stats])
#     std_currents  = np.array([s[1] for s in stats])
#     var_currents  = std_currents**2          # variance = std^2

#     segments = np.arange(1, 10)             # 1..9

#     fig_mv, axes_mv = plt.subplots(1, 2, figsize=(12, 5))

#     # Barplot 1: mean current
#     axes_mv[0].bar(segments, mean_currents, color='steelblue', edgecolor='black')
#     axes_mv[0].set_title('Mean Current per Segment')
#     axes_mv[0].set_xlabel('Segment')
#     axes_mv[0].set_ylabel('Mean Current (A)')
#     axes_mv[0].grid(True, alpha=0.3)

#     # Barplot 2: variance
#     axes_mv[1].bar(segments, var_currents, color='orange', edgecolor='black')
#     axes_mv[1].set_title('Current Variance per Segment')
#     axes_mv[1].set_xlabel('Segment')
#     axes_mv[1].set_ylabel('Variance (A²)')
#     axes_mv[1].grid(True, alpha=0.3)

#     plt.tight_layout()
#     plt.show()
# MAIN EXECUTION
# if __name__ == "__main__":
#     # FOLDER_PATH = input("Enter folder path with 9 CSV files: ").strip()
#     # FOLDER_PATH = "C:/Users/20250553/Desktop/EngD/ENGD_COURSES/TEAM_ASSIGNMENT/data"
#     FOLDER_PATH = "D:/EngD/Courses/team Assignment/code/file/EngD 2025-2026"
    
#     if not os.path.exists(FOLDER_PATH):
#         print("Error: Folder not found!")
#         exit(1)
    
#     # Default parameters (customize here)
#     WINDOW_SECONDS = 60      # 2 minutes
#     FILTER_TYPE = "low"       # "low", "high", "bandpass"
#     CUTOFF_HZ = 0.01           # Filter cutoff frequency
#     FILTER_ORDER = 4          # Filter order
#     OVERLAP=30

#     print("Starting electrolysis analysis...")
#     try:
#         dfs_filtered, stats, h2_data, o2_data = analyze_and_plot(
#             FOLDER_PATH, 
#             window_duration_s=WINDOW_SECONDS,
#             overlap=OVERLAP,
#             filter_type=FILTER_TYPE,
#             cutoff_hz=CUTOFF_HZ,
#             filter_order=FILTER_ORDER
#         )
#         print("\nAnalysis completed successfully!")
#         print("Close all plot windows to exit.")
#     except Exception as e:
#         print(f"Error during analysis: {e}")
