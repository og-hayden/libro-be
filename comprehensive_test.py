#!/usr/bin/env python3
"""
Comprehensive API Test Suite for Libro Bible Reader Backend
Tests all endpoints to verify full functionality
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:5000/api"

class APITester:
    def __init__(self):
        self.access_token = None
        self.test_results = []
        
    def log_test(self, test_name, success, details=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details
        })
    
    def test_auth_register(self):
        """Test user registration"""
        try:
            response = requests.post(f"{BASE_URL}/auth/register", json={
                "username": f"testuser_{int(datetime.now().timestamp())}",
                "email": f"test_{int(datetime.now().timestamp())}@example.com",
                "password": "testpass123"
            })
            
            if response.status_code == 201:
                data = response.json()
                self.log_test("User Registration", True, f"User created with ID: {data.get('user', {}).get('id')}")
                return True
            else:
                self.log_test("User Registration", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("User Registration", False, f"Exception: {str(e)}")
            return False
    
    def test_auth_login(self):
        """Test user login and get access token"""
        try:
            response = requests.post(f"{BASE_URL}/auth/login", json={
                "username": "debuguser",
                "password": "debugpass123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.log_test("User Login", True, "Access token obtained")
                return True
            else:
                self.log_test("User Login", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("User Login", False, f"Exception: {str(e)}")
            return False
    
    def test_auth_profile(self):
        """Test user profile endpoint"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("User Profile", True, f"Username: {data.get('username')}")
                return True
            else:
                self.log_test("User Profile", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("User Profile", False, f"Exception: {str(e)}")
            return False
    
    def test_bible_books(self):
        """Test Bible books endpoint"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(f"{BASE_URL}/bible/books", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                books = data.get('books', [])
                self.log_test("Bible Books", True, f"Found {len(books)} books")
                return True
            else:
                self.log_test("Bible Books", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Bible Books", False, f"Exception: {str(e)}")
            return False
    
    def test_bible_chapter(self):
        """Test Bible chapter endpoint"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(f"{BASE_URL}/bible/books/5/chapters/1", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                verses = data.get('verses', [])
                self.log_test("Bible Chapter", True, f"Genesis 1 has {len(verses)} verses")
                return True
            else:
                self.log_test("Bible Chapter", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Bible Chapter", False, f"Exception: {str(e)}")
            return False
    
    def test_bible_reference(self):
        """Test Bible reference lookup"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(f"{BASE_URL}/bible/reference?ref=John 3:16", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Bible Reference", True, f"Found: {data.get('reference')}")
                return True
            else:
                self.log_test("Bible Reference", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Bible Reference", False, f"Exception: {str(e)}")
            return False
    
    def test_strongs_stats(self):
        """Test Strong's statistics"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(f"{BASE_URL}/strongs/stats", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Strong's Stats", True, f"Total mappings: {data.get('total_mappings')}")
                return True
            else:
                self.log_test("Strong's Stats", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Strong's Stats", False, f"Exception: {str(e)}")
            return False
    
    def test_strongs_lookup(self):
        """Test Strong's lookup"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(f"{BASE_URL}/strongs/lookup/H430", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Strong's Lookup", True, f"Found H430: {data.get('definition', 'No definition')[:50]}...")
                return True
            else:
                self.log_test("Strong's Lookup", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Strong's Lookup", False, f"Exception: {str(e)}")
            return False
    
    def test_notes_create(self):
        """Test creating a note"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.post(f"{BASE_URL}/notes", 
                headers=headers,
                json={
                    "verse_id": 10,
                    "note_text": f"Test note created at {datetime.now()}"
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                self.log_test("Notes Create", True, f"Note ID: {data.get('note', {}).get('id')}")
                return data.get('note', {}).get('id')
            else:
                self.log_test("Notes Create", False, f"Status: {response.status_code}, Response: {response.text}")
                return None
        except Exception as e:
            self.log_test("Notes Create", False, f"Exception: {str(e)}")
            return None
    
    def test_notes_list(self):
        """Test listing notes"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(f"{BASE_URL}/notes", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                notes = data.get('notes', [])
                self.log_test("Notes List", True, f"Found {len(notes)} notes")
                return True
            else:
                self.log_test("Notes List", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Notes List", False, f"Exception: {str(e)}")
            return False
    
    def test_ai_summary(self):
        """Test AI verse summary"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.post(f"{BASE_URL}/analysis/summary",
                headers=headers,
                json={
                    "verse_range_start": 10,
                    "verse_range_end": 10,
                    "perspectives": ["catholic"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                cached = data.get('cached', False)
                self.log_test("AI Summary", True, f"Generated summary (cached: {cached})")
                return True
            else:
                self.log_test("AI Summary", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("AI Summary", False, f"Exception: {str(e)}")
            return False
    
    def test_ai_question(self):
        """Test AI question answering"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.post(f"{BASE_URL}/analysis/question",
                headers=headers,
                json={
                    "verse_range_start": 10,
                    "question": "What is the significance of creation?",
                    "perspectives": ["catholic"]
                }
            )
            
            if response.status_code == 201 or response.status_code == 200:
                data = response.json()
                self.log_test("AI Question", True, f"Analysis ID: {data.get('id')}")
                return True
            else:
                self.log_test("AI Question", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("AI Question", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Comprehensive API Test Suite")
        print("=" * 50)
        
        # Authentication tests
        print("\n📝 Authentication Tests")
        self.test_auth_register()
        if not self.test_auth_login():
            print("❌ Cannot continue without login - stopping tests")
            return
        self.test_auth_profile()
        
        # Bible content tests
        print("\n📖 Bible Content Tests")
        self.test_bible_books()
        self.test_bible_chapter()
        self.test_bible_reference()
        
        # Strong's concordance tests
        print("\n🔍 Strong's Concordance Tests")
        self.test_strongs_stats()
        self.test_strongs_lookup()
        
        # Notes tests
        print("\n📝 Notes Tests")
        note_id = self.test_notes_create()
        self.test_notes_list()
        
        # AI analysis tests
        print("\n🤖 AI Analysis Tests")
        self.test_ai_summary()
        self.test_ai_question()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All tests passed! Backend is fully functional.")
        else:
            print("⚠️  Some tests failed. Check the details above.")
            failed_tests = [r['test'] for r in self.test_results if not r['success']]
            print(f"Failed tests: {', '.join(failed_tests)}")

if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests()
