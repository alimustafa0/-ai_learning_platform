// Unified follow button handler
document.addEventListener('DOMContentLoaded', function() {

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

    // Function to update ALL buttons for a specific user
    function updateAllUserButtons(userId, isFollowing) {
        // Select all buttons for this user (across the entire page)
        const userButtons = document.querySelectorAll(`.follow-btn[data-user-id="${userId}"], .follow-btn-mini[data-user-id="${userId}"], .review-follow-btn[data-user-id="${userId}"], .profile-follow-btn[data-user-id="${userId}"]`);

        userButtons.forEach(button => {
            const icon = button.querySelector('i');
            const textSpan = button.querySelector('span');

            if (button.classList.contains('profile-follow-btn')) {
                // Profile page button
                if (isFollowing) {
                    button.classList.remove('btn-primary');
                    button.classList.add('btn-outline-primary');
                    icon.classList.remove('fa-user-plus');
                    icon.classList.add('fa-user-minus');
                    if (textSpan) textSpan.textContent = 'Unfollow';
                } else {
                    button.classList.remove('btn-outline-primary');
                    button.classList.add('btn-primary');
                    icon.classList.remove('fa-user-minus');
                    icon.classList.add('fa-user-plus');
                    if (textSpan) textSpan.textContent = 'Follow';
                }
            } else {
                // Mini buttons (comments, reviews, activity feed)
                if (isFollowing) {
                    icon.classList.remove('fa-user-plus', 'text-secondary');
                    icon.classList.add('fa-user-check', 'text-primary');
                } else {
                    icon.classList.remove('fa-user-check', 'text-primary');
                    icon.classList.add('fa-user-plus', 'text-secondary');
                }
            }
        });
    }

    // Handle all follow buttons
    document.querySelectorAll('.follow-btn, .follow-btn-mini, .review-follow-btn, .profile-follow-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const userId = this.dataset.userId;
            const button = this;

            fetch(`/accounts/follow/${userId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Update ALL buttons for this user on the page
                    updateAllUserButtons(userId, data.is_following);

                    // Update follower count on profile page if it exists
                    const followerCount = document.querySelector('.follower-count');
                    if (followerCount) {
                        followerCount.textContent = data.followers_count;
                    }
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });
});
