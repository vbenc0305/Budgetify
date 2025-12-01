// src/components/FeatureCarousel.jsx
import React, { useState } from "react";
import "./styles/FeatureCarousel.css"; // EZ KELL, hogy működjön a stílus



export default function FeatureCarousel({
                                            mainTitle,    // pl. "Miért érdemes ezt a projektet követni?"
                                            subTitle,     // pl. egy rövidebb alcím a carousel fölé
                                            description,  // pl. egy rövid bevezető szöveg a carousel fölé
                                            slides = defaultSlides, // opcionálisan átadható slide-ok tömbje
                                        }) {
    // Melyik slide (0, 1 vagy 2) legyen éppen aktív
    const [currentIndex, setCurrentIndex] = useState(0);

    // Következő gomb kattintás
    const goNext = () => {
        setCurrentIndex((prev) => (prev + 1) % slides.length);
    };

    // Előző gomb kattintás
    const goPrev = () => {
        setCurrentIndex((prev) => (prev - 1 + slides.length) % slides.length);
    };

    // Direkt módon kattintva a pöttyökre
    const goToIndex = (index) => {
        setCurrentIndex(index);
    };

    return (
        <div className="carousel-container">
            {/* MainTitle */}
            {mainTitle && (
                <h2 className="home-section-title text-center mb-2">
                    {mainTitle}
                </h2>
            )}

            {/* SubTitle */}
            {subTitle && (
                <h3 className="home-section-subtitle text-center mb-4">
                    {subTitle}
                </h3>
            )}

            {/* Description */}
            {description && (
                <p className="home-section-description text-center mb-6">
                    {description}
                </p>
            )}

            {/* A körvonalként megjelenő doboz */}
            <div className="carousel-box">
                {/* Balra mutató nyíl */}
                <button className="carousel-arrow left-arrow" onClick={goPrev}>
                    &#10094;
                </button>

                {/* Magában a dobozban a jelenlegi slide tartalma */}
                <div className="carousel-content">
                    <h4 className="carousel-title">{slides[currentIndex].title}</h4>
                    <p className="carousel-description">
                        {slides[currentIndex].description}
                    </p>
                </div>

                {/* Jobbra mutató nyíl */}
                <button className="carousel-arrow right-arrow" onClick={goNext}>
                    &#10095;
                </button>
            </div>

            {/* A pöttyök („dots”) az alján */}
            <div className="carousel-dots">
                {slides.map((_, idx) => (
                    <span
                        key={idx}
                        className={"carousel-dot " + (idx === currentIndex ? "active" : "")}
                        onClick={() => goToIndex(idx)}
                    />
                ))}
            </div>
        </div>
    );
}
