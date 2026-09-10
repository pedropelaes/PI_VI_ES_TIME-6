import React, { forwardRef } from 'react';
import './Grid.css';

interface GridProps {
    children: React.ReactNode;
}

export const Grid = forwardRef<HTMLDivElement, GridProps>(function Grid({ children }, ref) {
    return (
        <div className="generic-grid" ref={ref}>
            {children}
        </div>
    );
});