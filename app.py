def render_home():
    """
    Home / landing page:
    - top: banner (assets/banner.jpg)
    - middle: Department of CSE - AIML (centered)
    - bottom: Get started button (centered)
    - clicking Get started sets st.session_state.show_login = True and shows login panel below
    """
    banner_path = "assets/banner.jpg"
    # make sure CSS from earlier is present; this CSS centers the content in a simple stack
    st.markdown(
        """
        <style>
        .home-stack { display:flex; flex-direction:column; align-items:center; justify-content:flex-start; gap:28px; padding:48px 24px; width:100%; box-sizing:border-box; }
        .banner-full { width:100%; max-width:1100px; border-radius:12px; object-fit:cover; }
        .dept-text { font-weight:700; font-size:20px; color:#efefef; margin-top:6px; text-align:center; }
        .cta-wrap { margin-top:18px; }
        .cta-btn { display:inline-block; padding:12px 22px; border-radius:10px; border:1px solid rgba(255,255,255,0.06); background:#0f1724; color:#fff; font-weight:600; text-decoration:none; }
        @media (max-width:900px) {
            .banner-full { max-width: 100%; }
            .dept-text { font-size:18px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="home-stack">', unsafe_allow_html=True)

    # Banner (top, centered)
    try:
        st.image(banner_path, use_column_width=True, caption=None, clamp=False)
    except Exception:
        # fallback placeholder
        st.image("https://via.placeholder.com/1100x180.png?text=Banner", use_column_width=True)

    # Department text
    st.markdown(f'<div class="dept-text">Department of CSE - AIML</div>', unsafe_allow_html=True)

    # Centered Get started
    st.markdown('<div class="cta-wrap" style="text-align:center;">', unsafe_allow_html=True)
    # NOTE: button returns True in the same run, so no need for st.experimental_rerun()
    if st.button("Get started →", key="get_started_center"):
        st.session_state.show_login = True
        # no experimental_rerun; the script will continue in this run and show the login panel below
    st.markdown('</div>', unsafe_allow_html=True)

    # If the user clicked get started and is not logged in, show login panel below
    if st.session_state.get("show_login", False) and not getattr(st.user, "is_logged_in", False):
        show_login_panel()

    st.markdown('</div>', unsafe_allow_html=True)
