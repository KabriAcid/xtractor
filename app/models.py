"""Database management using pure SQLite - no ORM"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

# Database configuration
DB_PATH = "data/xtractor.db"
os.makedirs("data", exist_ok=True)

# All 37 Nigerian states (36 states + FCT Abuja)
NIGERIAN_STATES = [
    "ABIA", "ADAMAWA", "AKWA IBOM", "ANAMBRA", "BAUCHI", "BAYELSA",
    "BENUE", "BORNO", "CROSS RIVER", "DELTA", "EBONYI", "EDO",
    "EKITI", "ENUGU", "GOMBE", "IMO", "JIGAWA", "KADUNA",
    "KANO", "KATSINA", "KEBBI", "KOGI", "KWARA", "LAGOS",
    "NASARAWA", "NIGER", "OGUN", "ONDO", "OSUN", "OYO",
    "PLATEAU", "RIVERS", "SOKOTO", "TARABA", "YOBE", "ZAMFARA",
    "FCT"  # Federal Capital Territory (Abuja)
]


def init_db():
    """Initialize database with schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # States table (pre-populated)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Populate states if empty
    cursor.execute('SELECT COUNT(*) FROM states')
    if cursor.fetchone()[0] == 0:
        for state_name in NIGERIAN_STATES:
            cursor.execute('INSERT INTO states (name) VALUES (?)', (state_name,))
    
    # LGAs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lgas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            state_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (state_id) REFERENCES states(id),
            UNIQUE(code, state_id)
        )
    ''')
    
    # Wards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            lga_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lga_id) REFERENCES lgas(id),
            UNIQUE(code, lga_id)
        )
    ''')
    
    # Extraction logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS extraction_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            total_lgas_extracted INTEGER DEFAULT 0,
            total_wards_extracted INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_state_name ON states(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lga_code ON lgas(code, state_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lga_state ON lgas(state_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ward_code ON wards(code, lga_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ward_lga ON wards(lga_id)')
    
    conn.commit()
    conn.close()


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    conn.execute('PRAGMA journal_mode=WAL')  # Write-ahead logging for better concurrency
    conn.execute('PRAGMA busy_timeout=5000')  # 5 second timeout
    try:
        yield conn
    finally:
        conn.close()


class DatabaseManager:
    """Manage database operations"""
    
    @staticmethod
    def save_extraction_data(extracted_data, filename):
        """Save extracted data to database - states are pre-populated"""
        with get_db() as conn:
            conn.isolation_level = None  # Autocommit mode
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA busy_timeout=5000')
            
            cursor = conn.cursor()
            lgas_created = 0
            wards_created = 0
            log_id = None
            
            try:
                # Create extraction log
                cursor.execute('''
                    INSERT INTO extraction_logs 
                    (filename, status) 
                    VALUES (?, ?)
                ''', (filename, 'in_progress'))
                log_id = cursor.lastrowid
                
                # Process hierarchical data structure
                # States are already in DB, just match by name
                for state_data in extracted_data.get('states', []):
                    state_name = state_data.get('name', '').strip().upper()
                    if not state_name:
                        continue
                    
                    # Get state ID from pre-populated states
                    cursor.execute(
                        'SELECT id FROM states WHERE UPPER(name) = ?',
                        (state_name,)
                    )
                    state_id_row = cursor.fetchone()
                    if not state_id_row:
                        continue
                    state_id = state_id_row[0]
                    
                    # Process LGAs in this state
                    for lga_data in state_data.get('lgas', []):
                        lga_name = lga_data.get('name', '').strip()
                        lga_code = lga_data.get('code', '').strip()
                        if not lga_name or not lga_code:
                            continue
                        
                        # Insert LGA (unique on code + state_id)
                        cursor.execute('''
                            INSERT OR IGNORE INTO lgas 
                            (name, code, state_id) 
                            VALUES (?, ?, ?)
                        ''', (lga_name, lga_code, state_id))
                        
                        cursor.execute(
                            'SELECT id FROM lgas WHERE code = ? AND state_id = ?',
                            (lga_code, state_id)
                        )
                        lga_id_row = cursor.fetchone()
                        if not lga_id_row:
                            continue
                        lga_id = lga_id_row[0]
                        lgas_created += 1
                        
                        # Process wards in this LGA
                        for ward_data in lga_data.get('wards', []):
                            ward_name = ward_data.get('name', '').strip()
                            ward_code = ward_data.get('code', '').strip()
                            if not ward_name or not ward_code:
                                continue
                            
                            # Insert ward (unique on code + lga_id)
                            cursor.execute('''
                                INSERT OR IGNORE INTO wards 
                                (name, code, lga_id) 
                                VALUES (?, ?, ?)
                            ''', (ward_name, ward_code, lga_id))
                            wards_created += 1
                
                # Update extraction log with success
                cursor.execute('''
                    UPDATE extraction_logs 
                    SET status = ?, 
                        total_lgas_extracted = ?, 
                        total_wards_extracted = ?,
                        completed_at = ?
                    WHERE id = ?
                ''', ('success', lgas_created, wards_created, datetime.utcnow().isoformat(), log_id))
                
                conn.commit()
                
                return {
                    'log_id': log_id,
                    'lgas_created': lgas_created,
                    'wards_created': wards_created,
                    'status': 'success'
                }
                
            except Exception as e:
                # Update log with error
                try:
                    cursor.execute('''
                        UPDATE extraction_logs 
                        SET status = ?, error_message = ?, completed_at = ?
                        WHERE id = ?
                    ''', ('failed', str(e), datetime.utcnow().isoformat(), log_id))
                    conn.commit()
                except:
                    pass
                raise
    
    @staticmethod
    def get_all_states():
        """Get all states"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, 
                       (SELECT COUNT(*) FROM lgas WHERE state_id = states.id) as lga_count
                FROM states
                ORDER BY name
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_lgas_by_state(state_id):
        """Get all LGAs in a state"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, code,
                       (SELECT COUNT(*) FROM wards WHERE lga_id = lgas.id) as ward_count
                FROM lgas
                WHERE state_id = ?
                ORDER BY code
            ''', (state_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_wards_by_lga(lga_id):
        """Get all wards in an LGA"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, code
                FROM wards
                WHERE lga_id = ?
                ORDER BY code
            ''', (lga_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_extraction_logs(limit=100):
        """Get recent extraction logs"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, filename, status, total_lgas_extracted, 
                       total_wards_extracted, error_message, created_at, completed_at
                FROM extraction_logs
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_database_stats():
        """Get database statistics"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as count FROM states')
            total_states = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM lgas')
            total_lgas = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM wards')
            total_wards = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM extraction_logs')
            total_extractions = cursor.fetchone()['count']
            
            return {
                'total_states': total_states,
                'total_lgas': total_lgas,
                'total_wards': total_wards,
                'total_extractions': total_extractions
            }
    
    @staticmethod
    def search(query, search_type='all'):
        """Search for states, LGAs, or wards"""
        results = {'states': [], 'lgas': [], 'wards': []}
        query = f"%{query}%"
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            if search_type in ['all', 'state']:
                cursor.execute('''
                    SELECT id, name
                    FROM states
                    WHERE name LIKE ?
                    LIMIT 20
                ''', (query,))
                results['states'] = [dict(row) for row in cursor.fetchall()]
            
            if search_type in ['all', 'lga']:
                cursor.execute('''
                    SELECT l.id, l.name, l.code, s.name as state
                    FROM lgas l
                    JOIN states s ON l.state_id = s.id
                    WHERE l.name LIKE ?
                    LIMIT 20
                ''', (query,))
                results['lgas'] = [dict(row) for row in cursor.fetchall()]
            
            if search_type in ['all', 'ward']:
                cursor.execute('''
                    SELECT w.id, w.name, w.code, l.name as lga
                    FROM wards w
                    JOIN lgas l ON w.lga_id = l.id
                    WHERE w.name LIKE ?
                    LIMIT 20
                ''', (query,))
                results['wards'] = [dict(row) for row in cursor.fetchall()]
        
        return results
    
    @staticmethod
    def export_all_data():
        """Export all data as JSON-compatible structure"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            export_data = {
                'export_time': datetime.utcnow().isoformat(),
                'states': []
            }
            
            cursor.execute('SELECT id, name FROM states ORDER BY name')
            states = [dict(row) for row in cursor.fetchall()]
            
            for state in states:
                state_data = {
                    'name': state['name'],
                    'lgas': []
                }
                
                cursor.execute('''
                    SELECT id, name, code FROM lgas 
                    WHERE state_id = ? ORDER BY code
                ''', (state['id'],))
                lgas = [dict(row) for row in cursor.fetchall()]
                
                for lga in lgas:
                    lga_data = {
                        'name': lga['name'],
                        'code': lga['code'],
                        'wards': []
                    }
                    
                    cursor.execute('''
                        SELECT name, code FROM wards 
                        WHERE lga_id = ? ORDER BY code
                    ''', (lga['id'],))
                    wards = [dict(row) for row in cursor.fetchall()]
                    
                    for ward in wards:
                        lga_data['wards'].append({
                            'name': ward['name'],
                            'code': ward['code']
                        })
                    
                    state_data['lgas'].append(lga_data)
                
                export_data['states'].append(state_data)
            
            return export_data


# Initialize database on import
init_db()

