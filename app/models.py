"""Database management using pure SQLite - no ORM"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

# Database configuration
DB_PATH = "data/xtractor.db"
os.makedirs("data", exist_ok=True)


def init_db():
    """Initialize database with schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # States table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_name TEXT NOT NULL UNIQUE,
            state_code TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # LGAs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lgas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lga_name TEXT NOT NULL,
            lga_code TEXT NOT NULL,
            state_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (state_id) REFERENCES states(id),
            UNIQUE(lga_name, state_id)
        )
    ''')
    
    # Wards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_name TEXT NOT NULL,
            ward_code TEXT NOT NULL,
            lga_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lga_id) REFERENCES lgas(id),
            UNIQUE(ward_name, lga_id)
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
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_state_name ON states(state_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lga_name ON lgas(lga_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lga_state ON lgas(state_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ward_name ON wards(ward_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ward_lga ON wards(lga_id)')
    
    conn.commit()
    conn.close()


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()


class DatabaseManager:
    """Manage database operations"""
    
    @staticmethod
    def save_extraction_data(extracted_data, filename):
        """Save extracted data to database"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            try:
                # Track counts
                lgas_created = 0
                wards_created = 0
                log_id = None
                
                # Create extraction log
                cursor.execute('''
                    INSERT INTO extraction_logs 
                    (filename, status) 
                    VALUES (?, ?)
                ''', (filename, 'in_progress'))
                log_id = cursor.lastrowid
                
                # Process states
                state_map = {}
                for state_data in extracted_data.get('states', []):
                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO states 
                            (state_name, state_code) 
                            VALUES (?, ?)
                        ''', (state_data['name'], state_data.get('code', '')))
                        
                        cursor.execute(
                            'SELECT id FROM states WHERE state_name = ?',
                            (state_data['name'],)
                        )
                        state_id = cursor.fetchone()[0]
                        state_map[state_data['name']] = state_id
                    except Exception as e:
                        print(f"Error saving state {state_data['name']}: {e}")
                
                # Process LGAs
                lga_map = {}
                for lga_data in extracted_data.get('lgas', []):
                    state_name = lga_data.get('state')
                    if state_name and state_name in state_map:
                        try:
                            state_id = state_map[state_name]
                            cursor.execute('''
                                INSERT OR IGNORE INTO lgas 
                                (lga_name, lga_code, state_id) 
                                VALUES (?, ?, ?)
                            ''', (lga_data['name'], lga_data.get('code', ''), state_id))
                            
                            cursor.execute(
                                'SELECT id FROM lgas WHERE lga_name = ? AND state_id = ?',
                                (lga_data['name'], state_id)
                            )
                            result = cursor.fetchone()
                            if result:
                                lga_id = result[0]
                                lga_map[f"{state_name}_{lga_data['name']}"] = lga_id
                                lgas_created += 1
                        except Exception as e:
                            print(f"Error saving LGA {lga_data['name']}: {e}")
                
                # Process Wards
                for ward_data in extracted_data.get('wards', []):
                    state_name = ward_data.get('state')
                    lga_name = ward_data.get('lga')
                    key = f"{state_name}_{lga_name}"
                    
                    if key in lga_map:
                        try:
                            lga_id = lga_map[key]
                            cursor.execute('''
                                INSERT OR IGNORE INTO wards 
                                (ward_name, ward_code, lga_id) 
                                VALUES (?, ?, ?)
                            ''', (ward_data['name'], ward_data.get('code', ''), lga_id))
                            wards_created += 1
                        except Exception as e:
                            print(f"Error saving ward {ward_data['name']}: {e}")
                
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
                cursor.execute('''
                    UPDATE extraction_logs 
                    SET status = ?, error_message = ?, completed_at = ?
                    WHERE id = ?
                ''', ('failed', str(e), datetime.utcnow().isoformat(), log_id))
                conn.commit()
                raise
    
    @staticmethod
    def get_all_states():
        """Get all states"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, state_name, state_code, 
                       (SELECT COUNT(*) FROM lgas WHERE state_id = states.id) as lga_count
                FROM states
                ORDER BY state_name
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_lgas_by_state(state_id):
        """Get all LGAs in a state"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, lga_name, lga_code,
                       (SELECT COUNT(*) FROM wards WHERE lga_id = lgas.id) as ward_count
                FROM lgas
                WHERE state_id = ?
                ORDER BY lga_name
            ''', (state_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_wards_by_lga(lga_id):
        """Get all wards in an LGA"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, ward_name, ward_code
                FROM wards
                WHERE lga_id = ?
                ORDER BY ward_name
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
                    SELECT id, state_name as name, state_code as code
                    FROM states
                    WHERE state_name LIKE ?
                    LIMIT 20
                ''', (query,))
                results['states'] = [dict(row) for row in cursor.fetchall()]
            
            if search_type in ['all', 'lga']:
                cursor.execute('''
                    SELECT l.id, l.lga_name as name, l.lga_code as code, s.state_name as state
                    FROM lgas l
                    JOIN states s ON l.state_id = s.id
                    WHERE l.lga_name LIKE ?
                    LIMIT 20
                ''', (query,))
                results['lgas'] = [dict(row) for row in cursor.fetchall()]
            
            if search_type in ['all', 'ward']:
                cursor.execute('''
                    SELECT w.id, w.ward_name as name, w.ward_code as code, l.lga_name as lga
                    FROM wards w
                    JOIN lgas l ON w.lga_id = l.id
                    WHERE w.ward_name LIKE ?
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
            
            cursor.execute('SELECT id, state_name, state_code FROM states ORDER BY state_name')
            states = [dict(row) for row in cursor.fetchall()]
            
            for state in states:
                state_data = {
                    'name': state['state_name'],
                    'code': state['state_code'],
                    'lgas': []
                }
                
                cursor.execute('''
                    SELECT id, lga_name, lga_code FROM lgas 
                    WHERE state_id = ? ORDER BY lga_name
                ''', (state['id'],))
                lgas = [dict(row) for row in cursor.fetchall()]
                
                for lga in lgas:
                    lga_data = {
                        'name': lga['lga_name'],
                        'code': lga['lga_code'],
                        'wards': []
                    }
                    
                    cursor.execute('''
                        SELECT ward_name, ward_code FROM wards 
                        WHERE lga_id = ? ORDER BY ward_name
                    ''', (lga['id'],))
                    wards = [dict(row) for row in cursor.fetchall()]
                    
                    for ward in wards:
                        lga_data['wards'].append({
                            'name': ward['ward_name'],
                            'code': ward['ward_code']
                        })
                    
                    state_data['lgas'].append(lga_data)
                
                export_data['states'].append(state_data)
            
            return export_data


# Initialize database on import
init_db()

