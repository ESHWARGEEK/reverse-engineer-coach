"""
Property-based tests for data model persistence
Feature: reverse-engineer-coach, Property 10: File Persistence Round-Trip
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from sqlalchemy.orm import Session
from tests.test_models import LearningProject, ReferenceSnippet, ProjectFile, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
from datetime import datetime


def create_test_session():
    """Create a fresh test database session"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


# Hypothesis strategies for generating test data
@st.composite
def learning_project_data(draw):
    """Generate valid learning project data"""
    return {
        "user_id": draw(st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789")),
        "title": draw(st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
        "target_repository": "https://github.com/" + draw(st.text(min_size=5, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz")) + "/repo",
        "architecture_topic": draw(st.sampled_from(["Concurrency", "Scheduler", "Database", "Network", "Cache"])),
        "status": draw(st.sampled_from(["created", "analyzing", "ready", "in_progress", "completed"])),
        "total_tasks": draw(st.integers(min_value=0, max_value=20)),
        "completed_tasks": draw(st.integers(min_value=0, max_value=20)),
        "completion_percentage": draw(st.floats(min_value=0.0, max_value=100.0))
    }


@st.composite
def project_file_data(draw):
    """Generate valid project file data"""
    return {
        "file_path": draw(st.text(min_size=3, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz")) + ".py",
        "content": draw(st.text(min_size=0, max_size=1000)),
        "language": draw(st.sampled_from(["python", "typescript", "javascript", "go", "rust"]))
    }


@st.composite
def reference_snippet_data(draw):
    """Generate valid reference snippet data"""
    start_line = draw(st.integers(min_value=1, max_value=100))
    return {
        "github_url": "https://github.com/test/repo/blob/main/file.py#L" + str(start_line),
        "file_path": "src/" + draw(st.text(min_size=3, max_size=15, alphabet="abcdefghijklmnopqrstuvwxyz")) + ".py",
        "start_line": start_line,
        "end_line": start_line + draw(st.integers(min_value=0, max_value=10)),
        "code_content": draw(st.text(min_size=1, max_size=500)),
        "commit_sha": draw(st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")),
        "explanation": draw(st.text(min_size=0, max_size=100))
    }


class TestDataModelPersistence:
    """
    Property 10: File Persistence Round-Trip
    Validates: Requirements 5.3
    
    For any code changes saved in the editor, retrieving the project should restore the exact same code content
    """

    @given(learning_project_data())
    @settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
    def test_learning_project_persistence_round_trip(self, project_data):
        """Test that LearningProject data persists correctly through save/load cycle"""
        # Ensure completed_tasks <= total_tasks
        assume(project_data["completed_tasks"] <= project_data["total_tasks"])
        
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create and save project
            project = LearningProject(**project_data)
            test_db.add(project)
            test_db.commit()
            
            # Retrieve project
            retrieved_project = test_db.query(LearningProject).filter_by(id=project.id).first()
            
            # Verify all data matches exactly
            assert retrieved_project is not None
            assert retrieved_project.user_id == project_data["user_id"]
            assert retrieved_project.title == project_data["title"]
            assert retrieved_project.target_repository == project_data["target_repository"]
            assert retrieved_project.architecture_topic == project_data["architecture_topic"]
            assert retrieved_project.status == project_data["status"]
            assert retrieved_project.total_tasks == project_data["total_tasks"]
            assert retrieved_project.completed_tasks == project_data["completed_tasks"]
            assert retrieved_project.completion_percentage == project_data["completion_percentage"]
        finally:
            test_db.close()

    @given(project_file_data())
    @settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_project_file_content_persistence_round_trip(self, file_data):
        """Test that ProjectFile content persists exactly through save/load cycle"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create a parent project first
            project = LearningProject(
                user_id="test_user",
                title="Test Project",
                target_repository="https://github.com/test/repo",
                architecture_topic="Testing",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            # Create and save project file
            project_file = ProjectFile(
                project_id=project.id,
                **file_data
            )
            test_db.add(project_file)
            test_db.commit()
            
            # Retrieve project file
            retrieved_file = test_db.query(ProjectFile).filter_by(id=project_file.id).first()
            
            # Verify content matches exactly (critical for code persistence)
            assert retrieved_file is not None
            assert retrieved_file.content == file_data["content"]
            assert retrieved_file.file_path == file_data["file_path"]
            assert retrieved_file.language == file_data["language"]
            assert retrieved_file.project_id == project.id
        finally:
            test_db.close()

    @given(reference_snippet_data())
    @settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_reference_snippet_persistence_round_trip(self, snippet_data):
        """Test that ReferenceSnippet data persists correctly through save/load cycle"""
        # Ensure start_line <= end_line
        assume(snippet_data["start_line"] <= snippet_data["end_line"])
        
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create and save reference snippet
            snippet = ReferenceSnippet(**snippet_data)
            test_db.add(snippet)
            test_db.commit()
            
            # Retrieve snippet
            retrieved_snippet = test_db.query(ReferenceSnippet).filter_by(id=snippet.id).first()
            
            # Verify all data matches exactly
            assert retrieved_snippet is not None
            assert retrieved_snippet.github_url == snippet_data["github_url"]
            assert retrieved_snippet.file_path == snippet_data["file_path"]
            assert retrieved_snippet.start_line == snippet_data["start_line"]
            assert retrieved_snippet.end_line == snippet_data["end_line"]
            assert retrieved_snippet.code_content == snippet_data["code_content"]
            assert retrieved_snippet.commit_sha == snippet_data["commit_sha"]
            assert retrieved_snippet.explanation == snippet_data["explanation"]
        finally:
            test_db.close()

    @given(st.text(min_size=1, max_size=1000))
    @settings(max_examples=5, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_large_code_content_persistence(self, large_content):
        """Test that large code content persists correctly"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create a parent project
            project = LearningProject(
                user_id="test_user",
                title="Large Content Test",
                target_repository="https://github.com/test/large-repo",
                architecture_topic="Performance",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            # Create project file with large content
            project_file = ProjectFile(
                project_id=project.id,
                file_path="large_file.py",
                content=large_content,
                language="python"
            )
            test_db.add(project_file)
            test_db.commit()
            
            # Retrieve and verify
            retrieved_file = test_db.query(ProjectFile).filter_by(id=project_file.id).first()
            assert retrieved_file.content == large_content
        finally:
            test_db.close()

    def test_multiple_files_same_project_persistence(self):
        """Test that multiple files in the same project persist independently"""
        # Create fresh database session
        test_db = create_test_session()
        
        try:
            # Create a parent project
            project = LearningProject(
                user_id="test_user",
                title="Multi-file Test",
                target_repository="https://github.com/test/multi-repo",
                architecture_topic="Architecture",
                status="created"
            )
            test_db.add(project)
            test_db.commit()
            
            # Create multiple files with different content
            files_data = [
                {"file_path": "main.py", "content": "print('Hello World')", "language": "python"},
                {"file_path": "utils.ts", "content": "export const helper = () => {}", "language": "typescript"},
                {"file_path": "config.json", "content": '{"key": "value"}', "language": "json"}
            ]
            
            created_files = []
            for file_data in files_data:
                project_file = ProjectFile(project_id=project.id, **file_data)
                test_db.add(project_file)
                created_files.append(project_file)
            
            test_db.commit()
            
            # Retrieve all files and verify each one
            for i, created_file in enumerate(created_files):
                retrieved_file = test_db.query(ProjectFile).filter_by(id=created_file.id).first()
                assert retrieved_file.content == files_data[i]["content"]
                assert retrieved_file.file_path == files_data[i]["file_path"]
                assert retrieved_file.language == files_data[i]["language"]
        finally:
            test_db.close()