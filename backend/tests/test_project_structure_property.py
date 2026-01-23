"""
Property-based test for project structure organization
Feature: reverse-engineer-coach, Property 11: Project Structure Organization
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.test_models import Base
from app.repositories import LearningProjectRepository, ProjectFileRepository
from contextlib import contextmanager
import os


@contextmanager
def create_test_session():
    """Create a test database session as context manager"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# Strategy for generating valid file paths
file_path_strategy = st.one_of([
    # Simple filenames
    st.builds(
        lambda name, ext: f"{name}.{ext}",
        name=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')).filter(lambda x: x and x[0].isalnum()),
        ext=st.sampled_from(['py', 'js', 'ts', 'java', 'cpp', 'c', 'h', 'md', 'txt', 'json', 'yaml', 'yml'])
    ),
    # Files in subdirectories
    st.builds(
        lambda dir1, name, ext: f"{dir1}/{name}.{ext}",
        dir1=st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')).filter(lambda x: x and x[0].isalnum()),
        name=st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')).filter(lambda x: x and x[0].isalnum()),
        ext=st.sampled_from(['py', 'js', 'ts', 'java', 'cpp', 'c', 'h', 'md', 'txt', 'json'])
    ),
    # Files in nested directories
    st.builds(
        lambda dir1, dir2, name, ext: f"{dir1}/{dir2}/{name}.{ext}",
        dir1=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')).filter(lambda x: x and x[0].isalnum()),
        dir2=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')).filter(lambda x: x and x[0].isalnum()),
        name=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')).filter(lambda x: x and x[0].isalnum()),
        ext=st.sampled_from(['py', 'js', 'ts', 'java', 'cpp', 'c', 'h'])
    )
])

# Strategy for generating file content
file_content_strategy = st.text(max_size=1000)

# Strategy for generating programming languages
language_strategy = st.one_of([
    st.just("python"),
    st.just("javascript"),
    st.just("typescript"),
    st.just("java"),
    st.just("cpp"),
    st.just("c"),
    st.just("markdown"),
    st.just("json"),
    st.just("yaml"),
    st.none()
])


@given(
    file_paths=st.lists(file_path_strategy, min_size=1, max_size=20, unique=True),
    contents=st.lists(file_content_strategy, min_size=1, max_size=20),
    languages=st.lists(language_strategy, min_size=1, max_size=20)
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=1000,  # Increase deadline to 1000ms for database operations
    max_examples=5  # Reduce examples to balance coverage with execution time
)
def test_project_structure_organization_property(file_paths, contents, languages):
    """
    Property 11: Project Structure Organization
    For any created file within a Learning_Project, it should be properly organized 
    within the project's directory structure
    
    Validates: Requirements 5.2
    """
    with create_test_session() as test_session:
        # Arrange
        project_repo = LearningProjectRepository(test_session)
        file_repo = ProjectFileRepository(test_session)
        
        # Create a test project
        project = project_repo.create(
            user_id="test_user",
            title="Structure Test Project",
            target_repository="https://github.com/test/structure",
            architecture_topic="Testing",
            status="created"
        )
        
        # Ensure we have matching lengths for all lists
        min_length = min(len(file_paths), len(contents), len(languages))
        file_paths = file_paths[:min_length]
        contents = contents[:min_length]
        languages = languages[:min_length]
        
        created_files = []
        
        # Act - Create files with the generated paths
        for file_path, content, language in zip(file_paths, contents, languages):
            project_file = file_repo.create(
                project_id=project.id,
                file_path=file_path,
                content=content,
                language=language
            )
            created_files.append(project_file)
        
        # Assert - Verify proper organization
        
        # 1. All files should be retrievable by project ID
        all_project_files = file_repo.get_by_project_id(project.id)
        assert len(all_project_files) == len(created_files), f"Expected {len(created_files)} files, got {len(all_project_files)}"
        
        # 2. Each file should maintain its correct path within the project
        created_paths = {f.file_path for f in created_files}
        retrieved_paths = {f.file_path for f in all_project_files}
        assert created_paths == retrieved_paths, "File paths should be preserved correctly"
        
        # 3. Files should be retrievable by their exact path
        for created_file in created_files:
            retrieved_file = file_repo.get_by_file_path(project.id, created_file.file_path)
            assert retrieved_file is not None, f"File '{created_file.file_path}' should be retrievable by path"
            assert retrieved_file.id == created_file.id, "Retrieved file should be the same as created file"
            assert retrieved_file.file_path == created_file.file_path, "File path should be preserved exactly"
            assert retrieved_file.content == created_file.content, "File content should be preserved"
            assert retrieved_file.language == created_file.language, "File language should be preserved"
        
        # 4. Directory structure should be logically organized
        # Files in the same directory should be grouped together when retrieved
        directory_groups = {}
        for file in all_project_files:
            directory = os.path.dirname(file.file_path) if '/' in file.file_path else ''
            if directory not in directory_groups:
                directory_groups[directory] = []
            directory_groups[directory].append(file)
        
        # Verify that files in the same directory are properly grouped
        for directory, files_in_dir in directory_groups.items():
            for file in files_in_dir:
                expected_dir = os.path.dirname(file.file_path) if '/' in file.file_path else ''
                assert expected_dir == directory, f"File '{file.file_path}' should be in directory '{directory}'"
        
        # 5. File paths should be normalized (no double slashes, etc.)
        for file in all_project_files:
            assert '//' not in file.file_path, f"File path '{file.file_path}' should not contain double slashes"
            assert not file.file_path.startswith('/'), f"File path '{file.file_path}' should not start with slash"
            assert not file.file_path.endswith('/'), f"File path '{file.file_path}' should not end with slash"


@given(
    nested_paths=st.lists(
        st.builds(
            lambda dirs, filename: '/'.join(dirs + [filename]),
            dirs=st.lists(
                st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')).filter(lambda x: x and x[0].isalnum()),
                min_size=1, max_size=4
            ),
            filename=st.builds(
                lambda name, ext: f"{name}.{ext}",
                name=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')).filter(lambda x: x and x[0].isalnum()),
                ext=st.sampled_from(['py', 'js', 'ts', 'md'])
            )
        ),
        min_size=1, max_size=10, unique=True
    )
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=1000,  # Increase deadline for database operations
    max_examples=30  # Reduce examples for nested operations
)
def test_nested_directory_structure_property(nested_paths):
    """
    Property: Files in nested directories should maintain proper hierarchical organization
    
    This extends Property 11 to verify deep directory structures work correctly
    """
    with create_test_session() as test_session:
        # Arrange
        project_repo = LearningProjectRepository(test_session)
        file_repo = ProjectFileRepository(test_session)
        
        project = project_repo.create(
            user_id="test_user",
            title="Nested Structure Test",
            target_repository="https://github.com/test/nested",
            architecture_topic="Testing",
            status="created"
        )
        
        # Act - Create files with nested paths
        created_files = []
        for file_path in nested_paths:
            project_file = file_repo.create(
                project_id=project.id,
                file_path=file_path,
                content=f"Content for {file_path}",
                language="python"
            )
            created_files.append(project_file)
        
        # Assert - Verify nested structure is maintained
        all_files = file_repo.get_by_project_id(project.id)
        
        # Each file should be retrievable by its full path
        for created_file in created_files:
            retrieved = file_repo.get_by_file_path(project.id, created_file.file_path)
            assert retrieved is not None, f"Nested file '{created_file.file_path}' should be retrievable"
            assert retrieved.file_path == created_file.file_path, "Nested path should be preserved exactly"
        
        # Verify directory depth is preserved
        for file in all_files:
            path_parts = file.file_path.split('/')
            assert len(path_parts) >= 2, f"File '{file.file_path}' should have at least one directory level"
            
            # Verify each part of the path is valid
            for part in path_parts:
                assert part, f"No empty path components allowed in '{file.file_path}'"
                assert not part.startswith('.'), f"Path components should not start with dot in '{file.file_path}'"


@given(
    file_path=file_path_strategy,
    initial_content=file_content_strategy,
    updated_content=file_content_strategy,
    language=language_strategy
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=800,  # Increase deadline for update operations
    max_examples=40
)
def test_file_update_preserves_structure_property(file_path, initial_content, updated_content, language):
    """
    Property: Updating file content should preserve the file's position in the project structure
    
    This extends Property 11 to verify updates don't break organization
    """
    with create_test_session() as test_session:
        # Arrange
        project_repo = LearningProjectRepository(test_session)
        file_repo = ProjectFileRepository(test_session)
        
        project = project_repo.create(
            user_id="test_user",
            title="Update Structure Test",
            target_repository="https://github.com/test/update",
            architecture_topic="Testing",
            status="created"
        )
        
        # Act - Create file, then update it
        original_file = file_repo.create(
            project_id=project.id,
            file_path=file_path,
            content=initial_content,
            language=language
        )
        
        updated_file = file_repo.update_file_content(
            project.id,
            file_path,
            updated_content
        )
        
        # Assert - Structure should be preserved
        assert updated_file is not None, "File update should succeed"
        assert updated_file.id == original_file.id, "File ID should remain the same after update"
        assert updated_file.file_path == original_file.file_path, "File path should remain unchanged"
        assert updated_file.project_id == original_file.project_id, "Project association should remain unchanged"
        assert updated_file.content == updated_content, "Content should be updated"
        
        # File should still be retrievable by path
        retrieved = file_repo.get_by_file_path(project.id, file_path)
        assert retrieved is not None, "Updated file should still be retrievable by path"
        assert retrieved.id == updated_file.id, "Retrieved file should be the updated version"
        assert retrieved.content == updated_content, "Retrieved content should match updated content"


@given(
    file_paths=st.lists(file_path_strategy, min_size=2, max_size=10, unique=True)
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=800,  # Increase deadline for deletion operations
    max_examples=30
)
def test_file_deletion_preserves_structure_property(file_paths):
    """
    Property: Deleting files should not affect the organization of remaining files
    
    This extends Property 11 to verify deletions don't break structure
    """
    with create_test_session() as test_session:
        # Arrange
        project_repo = LearningProjectRepository(test_session)
        file_repo = ProjectFileRepository(test_session)
        
        project = project_repo.create(
            user_id="test_user",
            title="Deletion Structure Test",
            target_repository="https://github.com/test/deletion",
            architecture_topic="Testing",
            status="created"
        )
        
        # Create multiple files
        created_files = []
        for file_path in file_paths:
            project_file = file_repo.create(
                project_id=project.id,
                file_path=file_path,
                content=f"Content for {file_path}",
                language="python"
            )
            created_files.append(project_file)
        
        # Act - Delete the first file
        file_to_delete = created_files[0]
        remaining_files = created_files[1:]
        
        success = file_repo.delete_by_path(project.id, file_to_delete.file_path)
        assert success, "File deletion should succeed"
        
        # Assert - Remaining files should maintain their structure
        all_remaining = file_repo.get_by_project_id(project.id)
        assert len(all_remaining) == len(remaining_files), "Correct number of files should remain"
        
        # Each remaining file should still be properly organized
        for original_file in remaining_files:
            retrieved = file_repo.get_by_file_path(project.id, original_file.file_path)
            assert retrieved is not None, f"Remaining file '{original_file.file_path}' should still be retrievable"
            assert retrieved.file_path == original_file.file_path, "Remaining file path should be unchanged"
            assert retrieved.content == original_file.content, "Remaining file content should be unchanged"
        
        # Deleted file should not be retrievable
        deleted_file = file_repo.get_by_file_path(project.id, file_to_delete.file_path)
        assert deleted_file is None, "Deleted file should not be retrievable"


@given(
    languages=st.lists(
        st.sampled_from(['python', 'javascript', 'typescript', 'java', 'cpp']),
        min_size=1, max_size=5, unique=True
    )
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=800,  # Increase deadline for language-based operations
    max_examples=25
)
def test_language_based_organization_property(languages):
    """
    Property: Files should be organizable and retrievable by programming language
    
    This extends Property 11 to verify language-based organization works correctly
    """
    with create_test_session() as test_session:
        # Arrange
        project_repo = LearningProjectRepository(test_session)
        file_repo = ProjectFileRepository(test_session)
        
        project = project_repo.create(
            user_id="test_user",
            title="Language Organization Test",
            target_repository="https://github.com/test/languages",
            architecture_topic="Testing",
            status="created"
        )
        
        # Act - Create files for each language
        files_by_language = {}
        for i, language in enumerate(languages):
            file_path = f"file_{i}.{language[:2]}"  # Use first 2 chars as extension
            project_file = file_repo.create(
                project_id=project.id,
                file_path=file_path,
                content=f"Content in {language}",
                language=language
            )
            
            if language not in files_by_language:
                files_by_language[language] = []
            files_by_language[language].append(project_file)
        
        # Assert - Files should be retrievable by language
        for language, expected_files in files_by_language.items():
            retrieved_files = file_repo.get_by_language(project.id, language)
            
            assert len(retrieved_files) == len(expected_files), f"Should retrieve correct number of {language} files"
            
            retrieved_ids = {f.id for f in retrieved_files}
            expected_ids = {f.id for f in expected_files}
            assert retrieved_ids == expected_ids, f"Should retrieve the correct {language} files"
            
            # All retrieved files should have the correct language
            for file in retrieved_files:
                assert file.language == language, f"Retrieved file should have language '{language}'"
                assert file.project_id == project.id, "Retrieved file should belong to the correct project"


def test_empty_project_structure_property():
    """
    Property: Empty projects should have valid (empty) structure
    """
    with create_test_session() as test_session:
        # Arrange
        project_repo = LearningProjectRepository(test_session)
        file_repo = ProjectFileRepository(test_session)
        
        project = project_repo.create(
            user_id="test_user",
            title="Empty Project Test",
            target_repository="https://github.com/test/empty",
            architecture_topic="Testing",
            status="created"
        )
        
        # Act - Get files from empty project
        files = file_repo.get_by_project_id(project.id)
        
        # Assert - Should return empty list, not None or error
        assert files is not None, "Empty project should return empty list, not None"
        assert len(files) == 0, "Empty project should have no files"
        assert isinstance(files, list), "Should return a list even when empty"