import { useId } from 'react';
import { Check } from 'lucide-react';
import { MASCOTS } from '../mascots';
import useMascot from '../useMascot';
import './MascotPicker.css';

export default function MascotPicker({ language = 'vi' }) {
  const { mascot, setMascot } = useMascot();
  const groupName = useId();
  const vi = language === 'vi';

  return (
    <fieldset className="mascot-picker">
      <legend>{vi ? 'Người bạn đồng hành' : 'Your companion'}</legend>
      <p className="mascot-picker__hint">
        {vi ? 'Chọn chibi xuất hiện trong lời chào và các minh họa. Lưu trên trình duyệt này.' : 'Choose the chibi for greetings and illustrations. Saved in this browser.'}
      </p>
      <div className="mascot-picker__options">
        {MASCOTS.map(option => (
          <label key={option.id} className="mascot-picker__option">
            <input type="radio" name={groupName} value={option.id}
              checked={mascot.id === option.id} onChange={() => setMascot(option.id)} />
            <span className="mascot-picker__card">
              <span className="mascot-picker__art">
                <img src={option.idle} alt="" width="96" height="132" decoding="async"
                  style={{ transform: `scale(${option.scale})`, transformOrigin: 'bottom' }} />
              </span>
              <span className="mascot-picker__label">{option.name[vi ? 'vi' : 'en']}</span>
              <span className="mascot-picker__check" aria-hidden="true"><Check size={13} /></span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
