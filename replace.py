import os
import glob

replacements = {
    'class="block text-xs font-bold text-gray-600 dark:text-gray-300 uppercase mb-1"': 'class="form-label"',
    'class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"': 'class="form-label-sm"',
    'class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3 border-b border-gray-100 dark:border-gray-700 pb-2"': 'class="section-label"',
    'class="bg-gray-50 dark:bg-gray-900/40 p-3 rounded-xl border border-gray-100 dark:border-gray-700"': 'class="info-panel"',
    
    # modal backdrops - variations
    'class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center hidden opacity-0 transition-opacity duration-200 p-4"': 'class="modal-backdrop p-4"',
    'class="fixed inset-0 bg-black/50 z-50 hidden opacity-0 transition-opacity duration-300 flex items-center justify-center p-4"': 'class="modal-backdrop p-4"',
    'class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center hidden opacity-0 transition-opacity duration-300"': 'class="modal-backdrop"',
    'class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 hidden opacity-0 transition-opacity duration-300"': 'class="modal-backdrop"',
    'class="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 hidden opacity-0 transition-opacity duration-300 backdrop-blur-sm"': 'class="modal-backdrop"',

    # modal panel
    'class="bg-white dark:bg-darkCard rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden transform scale-95 transition-transform duration-300 border border-gray-100 dark:border-gray-700"': 'class="modal-panel w-full max-w-lg"',
    'class="bg-white dark:bg-darkCard w-full max-w-lg rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 transform scale-95 transition-transform duration-300 overflow-hidden"': 'class="modal-panel w-full max-w-lg"',
    'class="bg-white dark:bg-darkCard w-full max-w-2xl rounded-2xl shadow-2xl transform scale-95 transition-transform duration-300 overflow-hidden flex flex-col max-h-[90vh]"': 'class="modal-panel w-full max-w-2xl flex flex-col max-h-[90vh]"',
    'class="bg-white dark:bg-darkCard rounded-2xl max-w-lg w-full mx-4 shadow-2xl overflow-hidden border border-gray-200 dark:border-gray-700"': 'class="modal-panel w-full max-w-lg mx-4"',
    'class="bg-white dark:bg-darkCard w-full max-w-md rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 transform scale-95 transition-transform duration-300 overflow-hidden"': 'class="modal-panel w-full max-w-md"',
    'class="bg-white dark:bg-darkCard rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden transform scale-95 transition-transform duration-200 border border-gray-200 dark:border-gray-700 flex flex-col max-h-[90vh]"': 'class="modal-panel w-full max-w-2xl flex flex-col max-h-[90vh]"',
    
    # modal header
    'class="p-4 border-b border-gray-100 dark:border-gray-700/50 flex items-center justify-between bg-gray-50 dark:bg-gray-900/50"': 'class="modal-header"',
    'class="p-5 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-900/50"': 'class="modal-header"',
    'class="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 flex justify-between items-center"': 'class="modal-header"',
    'class="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center shrink-0 bg-gray-50 dark:bg-gray-900/50"': 'class="modal-header shrink-0"',
    'class="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 flex justify-between items-center shrink-0"': 'class="modal-header shrink-0"',
    
    # modal footer
    'class="pt-4 border-t border-gray-100 dark:border-gray-700/50 flex justify-end gap-3"': 'class="modal-footer"',
    'class="p-5 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 flex justify-end gap-3"': 'class="modal-footer"',
    'class="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 flex justify-end gap-3"': 'class="modal-footer"',
    'class="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3 shrink-0 bg-gray-50 dark:bg-gray-900/50"': 'class="modal-footer shrink-0"',
    
    # table th
    'class="py-4 px-4 text-xs font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider text-center"': 'class="table-th text-center"',
    'class="py-4 px-4 text-xs font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider"': 'class="table-th"',
    
    # kpi
    'class="text-2xl font-black text-slate-800 dark:text-white"': 'class="kpi-value"',
    'class="text-xs text-slate-500 dark:text-slate-400 mt-1 font-semibold"': 'class="kpi-variation"',
}

files = glob.glob('templates/*.html')
for file in files:
    with open(file, 'r') as f:
        content = f.read()
    
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    # Unify slate to gray in specific templates
    if file in ['templates/dashboard.html', 'templates/inventario.html']:
        content = content.replace('slate-', 'gray-')
        
    with open(file, 'w') as f:
        f.write(content)
