// courses/static/courses/js/comments.js

// ===== GLOBAL FUNCTIONS (defined outside DOMContentLoaded) =====

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Show notification function
function showNotification(message, type) {
    // Map type to Bootstrap alert class
    let alertClass = 'alert-info';
    if (type === 'success') alertClass = 'alert-success';
    if (type === 'error') alertClass = 'alert-danger';
    if (type === 'warning') alertClass = 'alert-warning';

    const notification = document.createElement('div');
    notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    notification.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// Function to attach event listeners to comment elements
function attachCommentEventListeners(commentElement) {
    if (!commentElement) return;

    // Remove existing listeners to prevent duplicates (using a flag)
    if (commentElement.hasAttribute('data-listeners-attached')) {
        return; // Skip if already attached
    }

    // Upvote button
    const upvoteBtn = commentElement.querySelector('.upvote-btn');
    if (upvoteBtn) {
        // Remove old listener if any (to prevent duplicates)
        upvoteBtn.removeEventListener('click', upvoteHandler);
        upvoteBtn.addEventListener('click', upvoteHandler);
    }

    // Reply button
    const replyBtn = commentElement.querySelector('.reply-btn');
    if (replyBtn) {
        replyBtn.removeEventListener('click', replyHandler);
        replyBtn.addEventListener('click', replyHandler);
    }

    // Edit button
    const editBtn = commentElement.querySelector('.edit-comment');
    if (editBtn) {
        editBtn.removeEventListener('click', editHandler);
        editBtn.addEventListener('click', editHandler);
    }

    // Delete button
    const deleteBtn = commentElement.querySelector('.delete-comment');
    if (deleteBtn) {
        deleteBtn.removeEventListener('click', deleteHandler);
        deleteBtn.addEventListener('click', deleteHandler);
    }

    // Mark as initialized
    commentElement.setAttribute('data-listeners-attached', 'true');
}

// Upvote handler
function upvoteHandler(e) {
    e.preventDefault();
    const commentId = this.dataset.commentId;
    const button = this; // Store reference to the button

    fetch(`/comments/${commentId}/upvote/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw { status: response.status, data: data };
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            const countSpan = button.querySelector('.upvote-count');
            countSpan.textContent = data.total_upvotes;

            if (data.user_upvoted) {
                button.classList.remove('btn-outline-primary');
                button.classList.add('btn-primary');
            } else {
                button.classList.remove('btn-primary');
                button.classList.add('btn-outline-primary');
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);

        // Handle 400 error (self-upvote)
        if (error.status === 400) {
            showNotification('You cannot upvote your own comment', 'warning');
        } else {
            showNotification('Error upvoting comment. Please try again.', 'error');
        }
    });
}

// Reply handler
function replyHandler(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
    }

    const button = e.currentTarget;
    const commentId = button.dataset.commentId;
    const commentAuthor = button.dataset.author;

    console.log('Reply button clicked for comment:', commentId);

    const replyForm = document.getElementById(`reply-form-${commentId}`);

    if (!replyForm) {
        console.error('Reply form not found for comment:', commentId);
        return;
    }

    document.querySelectorAll('.reply-form').forEach(form => {
        if (form.id !== `reply-form-${commentId}`) {
            form.style.display = 'none';
        }
    });

    const isHidden = replyForm.style.display === 'none' || !replyForm.style.display;

    if (isHidden) {
        replyForm.style.display = 'block';

        const textarea = replyForm.querySelector('textarea');
        if (textarea) {
            textarea.focus({ preventScroll: true });
        }

        document.getElementById('parent_id').value = commentId;
        document.querySelector('.cancel-reply').style.display = 'inline-block';
        document.querySelector('.reply-indicator').style.display = 'block';
        document.querySelector('.reply-indicator').innerHTML = `<i class="fas fa-reply me-1"></i>Replying to <strong>${commentAuthor}</strong>...`;
    } else {
        replyForm.style.display = 'none';
    }

    return false;
}

// Edit handler - FIXED to prevent multiple edit windows
function editHandler(e) {
    e.preventDefault();
    const commentId = this.dataset.commentId;
    const commentCard = document.getElementById(`comment-${commentId}`);
    const commentContent = commentCard.querySelector('.comment-content');

    // Check if edit form already exists for this comment
    if (commentCard.querySelector('.edit-form')) {
        return; // Don't create another edit form
    }

    const currentText = commentContent.textContent.trim();

    const editForm = document.createElement('div');
    editForm.className = 'edit-form mt-2';
    editForm.innerHTML = `
        <form action="/comments/${commentId}/edit/" method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="${getCookie('csrftoken')}">
            <textarea name="content" class="form-control form-control-sm mb-2" rows="3">${currentText}</textarea>
            <div class="d-flex gap-2">
                <button type="submit" class="btn btn-primary btn-sm">
                    <i class="fas fa-save me-1"></i>Save
                </button>
                <button type="button" class="btn btn-secondary btn-sm cancel-edit">
                    Cancel
                </button>
            </div>
        </form>
    `;

    commentContent.style.display = 'none';
    commentContent.parentNode.insertBefore(editForm, commentContent.nextSibling);

    // Handle cancel
    editForm.querySelector('.cancel-edit').addEventListener('click', function() {
        commentContent.style.display = 'block';
        editForm.remove();
    });

    // Handle form submission with AJAX
    editForm.querySelector('form').addEventListener('submit', function(e) {
        e.preventDefault();

        fetch(this.action, {
            method: 'POST',
            body: new FormData(this),
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                commentContent.innerHTML = data.content;
                commentContent.style.display = 'block';
                editForm.remove();
                showNotification('Comment updated!', 'success');
            } else {
                showNotification('Error updating comment.', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error updating comment.', 'error');
        });
    });
}

// Delete handler
function deleteHandler(e) {
    e.preventDefault();
    const commentId = this.dataset.commentId;
    const commentCard = document.getElementById(`comment-${commentId}`);

    if (confirm('Are you sure you want to delete this comment? This action cannot be undone.')) {
        fetch(`/comments/${commentId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                commentCard.remove();
                showNotification('Comment deleted successfully!', 'success');
            } else {
                showNotification('Error deleting comment.', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error deleting comment.', 'error');
        });
    }
}

// ===== DOM CONTENT LOADED (runs when page first loads) =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded - initializing comments');

    // Handle main comment form submission
    const mainCommentForm = document.querySelector('.main-comment-form');
    if (mainCommentForm) {
        mainCommentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('Main comment form submitted via AJAX');

            const formData = new FormData(this);

            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                console.log('Response data:', data);

                if (data.status === 'success') {
                    this.reset();

                    document.getElementById('parent_id').value = '';
                    document.querySelector('.cancel-reply').style.display = 'none';
                    document.querySelector('.reply-indicator').style.display = 'none';

                    const commentsList = document.querySelector('.comments-list');
                    if (commentsList) {
                        const emptyState = commentsList.querySelector('.text-center.py-5');
                        if (emptyState) {
                            emptyState.remove();
                        }

                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = data.html;
                        const newComment = tempDiv.firstElementChild;

                        commentsList.insertBefore(newComment, commentsList.firstChild);
                        attachCommentEventListeners(newComment);
                    }

                    const commentCount = document.querySelector('.badge.bg-secondary.ms-2');
                    if (commentCount) {
                        const currentCount = parseInt(commentCount.textContent) || 0;
                        commentCount.textContent = currentCount + 1;
                    }

                    showNotification('Comment posted successfully!', 'success');
                } else {
                    showNotification('Error posting comment. Please try again.', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error posting comment. Please try again.', 'error');
            });
        });
    }

    // Attach event listeners to all existing comments
    document.querySelectorAll('.comment-card').forEach(comment => {
        attachCommentEventListeners(comment);
    });

    // Handle reply form submissions
    document.addEventListener('submit', function(e) {
        if (e.target.classList.contains('reply-form-inline')) {
            e.preventDefault();
            e.stopPropagation();

            console.log('Reply form submitted');

            const form = e.target;
            const formData = new FormData(form);
            const actionUrl = form.action;

            fetch(actionUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            })
            .then(response => {
                console.log('Response status:', response.status);
                if (!response.ok) {
                    return response.json().then(err => { throw err; });
                }
                return response.json();
            })
            .then(data => {
                console.log('Reply response data:', data);

                if (data.status === 'success') {
                    form.closest('.reply-form').style.display = 'none';
                    form.reset();

                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = data.html;
                    const newComment = tempDiv.firstElementChild;

                    const commentCard = form.closest('.comment-card');
                    let repliesContainer = commentCard.querySelector('.replies');

                    if (!repliesContainer) {
                        repliesContainer = document.createElement('div');
                        repliesContainer.className = 'replies mt-3';
                        commentCard.querySelector('.card-body').appendChild(repliesContainer);
                    }

                    repliesContainer.appendChild(newComment);
                    attachCommentEventListeners(newComment);

                    const replyCountSpan = commentCard.querySelector('.reply-count');
                    if (replyCountSpan) {
                        const currentCount = parseInt(replyCountSpan.textContent) || 0;
                        replyCountSpan.textContent = currentCount + 1;
                    }

                    showNotification('Reply posted successfully!', 'success');
                } else {
                    showNotification('Error posting reply. Please try again.', 'error');
                }
            })
            .catch(error => {
                console.error('Fetch error:', error);
                showNotification('Error posting reply. Please try again.', 'error');
            });
        }
    });

    // Cancel reply button
    document.querySelector('.cancel-reply')?.addEventListener('click', function(e) {
        e.preventDefault();
        document.getElementById('parent_id').value = '';
        document.getElementById('id_content').placeholder = '';
        document.querySelector('.cancel-reply').style.display = 'none';
        document.querySelector('.reply-indicator').style.display = 'none';

        document.querySelectorAll('.reply-form').forEach(form => {
            form.style.display = 'none';
        });
    });

    // ===== LOAD MORE COMMENTS FUNCTIONALITY =====
    const loadMoreBtn = document.getElementById('load-more-comments');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', function() {
            const lessonId = this.dataset.lessonId;
            const nextPage = this.dataset.nextPage;
            const spinner = document.getElementById('load-more-spinner');
            const buttonText = document.getElementById('load-more-text');

            spinner.classList.remove('d-none');
            buttonText.textContent = 'Loading...';
            this.disabled = true;

            fetch(`/lessons/${lessonId}/comments/load-more/?page=${nextPage}`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const commentsList = document.getElementById('comments-list');

                    data.comments.forEach(commentHtml => {
                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = commentHtml;
                        const newComment = tempDiv.firstElementChild;
                        commentsList.appendChild(newComment);
                        // Force attach listeners to new comments
                        attachCommentEventListeners(newComment);
                    });

                    if (data.has_next) {
                        this.dataset.nextPage = data.next_page;
                        spinner.classList.add('d-none');
                        buttonText.textContent = 'Load More Comments';
                        this.disabled = false;
                    } else {
                        const container = document.getElementById('load-more-container');
                        if (container) container.remove();
                    }

                    const totalCountSpan = document.getElementById('total-comment-count');
                    if (totalCountSpan) {
                        totalCountSpan.textContent = data.total_comments;
                    }
                }
            })
            .catch(error => {
                console.error('Error loading comments:', error);
                spinner.classList.add('d-none');
                buttonText.textContent = 'Error - Try Again';
                this.disabled = false;

                setTimeout(() => {
                    buttonText.textContent = 'Load More Comments';
                }, 3000);
            });
        });
    }
});
