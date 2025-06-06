import Header from "@/components/Header";
import SearchInterface from "@/components/SearchInterface";

const Index = ({ loading, setLoading }: { loading: boolean; setLoading: (val: boolean) => void }) => {
  return (
    <div className="flex-1 bg-black text-white overflow-hidden">
      {/* Background gradient */}
      <div className="fixed inset-0 bg-gradient-to-br from-gray-900 via-black to-gray-900"></div>
      
      {/* Subtle pattern overlay */}
      <div 
        className="fixed inset-0 opacity-20"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, rgba(255,255,255,0.05) 1px, transparent 0)`,
          backgroundSize: '24px 24px'
        }}
      ></div>
      
      <div className="relative z-10">
        <Header />
        <SearchInterface loading={loading} setLoading={setLoading} />
      </div>
    </div>
  );
};

export default Index;
