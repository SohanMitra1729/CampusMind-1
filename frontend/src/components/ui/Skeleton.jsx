export const Skeleton = ({ className = '', ...props }) => {
  return (
    <div
      className={`cm-skeleton ${className}`}
      {...props}
    />
  );
};
