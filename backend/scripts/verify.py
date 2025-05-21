#!/usr/bin/env python3
"""
DocuQuery-AI verification script.
This script verifies that the user isolation and account fixes are working properly.
"""

import os
import sys
import uuid
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.db_models import User, File
from app.core.security import get_password_hash
from app.models.user import UserRole
from app.services.user_service import create_user
from app.services.file_service import get_user_files
from app.models.user import UserCreate

def verify_database_tables():
    """Verify that all required database tables exist."""
    db = SessionLocal()
    try:
        # Check users table
        users = db.query(User).all()
        print(f"✓ Users table exists with {len(users)} records")
        
        # Check files table
        try:
            files = db.query(File).all()
            print(f"✓ Files table exists with {len(files)} records")
        except Exception as e:
            print(f"✗ Files table error: {str(e)}")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Database verification error: {str(e)}")
        return False
    finally:
        db.close()

def verify_user_creation():
    """Verify that user creation works properly."""
    db = SessionLocal()
    try:
        # Create a test user
        test_email = f"test_{uuid.uuid4()}@example.com"
        test_user = UserCreate(
            email=test_email,
            password="test123",
            full_name="Test User",
            is_active=True,
            role=UserRole.USER
        )
        
        user = create_user(db, test_user)
        
        if user and user.id and user.email == test_email:
            print(f"✓ User creation works (ID: {user.id})")
            
            # Clean up test user
            db.delete(user)
            db.commit()
            print(f"✓ Test user deleted")
            return True
        else:
            print("✗ User creation failed")
            return False
    except Exception as e:
        print(f"✗ User creation error: {str(e)}")
        return False
    finally:
        db.close()

def verify_file_isolation():
    """Verify that files are properly isolated by user."""
    db = SessionLocal()
    try:
        # Create two test users
        email1 = f"filetest1_{uuid.uuid4()}@example.com"
        email2 = f"filetest2_{uuid.uuid4()}@example.com"
        
        user1 = UserCreate(
            email=email1,
            password="test123",
            full_name="File Test User 1",
            is_active=True,
            role=UserRole.USER
        )
        
        user2 = UserCreate(
            email=email2,
            password="test123",
            full_name="File Test User 2",
            is_active=True,
            role=UserRole.USER
        )
        
        db_user1 = create_user(db, user1)
        db_user2 = create_user(db, user2)
        
        # Create a test file record for user 1
        test_file = File(
            id=str(uuid.uuid4()),
            filename="test_file.txt",
            file_path="/tmp/test_file.txt",
            file_type="txt",
            user_id=db_user1.id,
            is_structured=False
        )
        
        db.add(test_file)
        db.commit()
        
        # Verify user 1 can see the file
        user1_files = get_user_files(db, db_user1.id)
        user2_files = get_user_files(db, db_user2.id)
        
        if len(user1_files) == 1 and len(user2_files) == 0:
            print("✓ File isolation works")
            
            # Clean up
            db.delete(test_file)
            db.delete(db_user1)
            db.delete(db_user2)
            db.commit()
            print("✓ Test data cleaned up")
            return True
        else:
            print(f"✗ File isolation check failed. User1 files: {len(user1_files)}, User2 files: {len(user2_files)}")
            return False
    except Exception as e:
        print(f"✗ File isolation error: {str(e)}")
        return False
    finally:
        db.close()

def main():
    """Main verification function."""
    print("====================================")
    print("DocuQuery-AI Verification")
    print("====================================")
    
    success = True
    
    print("\nVerifying database tables...")
    if not verify_database_tables():
        success = False
    
    print("\nVerifying user creation...")
    if not verify_user_creation():
        success = False
    
    print("\nVerifying file isolation...")
    if not verify_file_isolation():
        success = False
    
    print("\n====================================")
    if success:
        print("✓ All checks passed!")
    else:
        print("✗ Some checks failed. Please review the output above.")
    print("====================================")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 